#!/usr/bin/env python3
"""
Python implementation of MMDVM modem interface
"""

from dataclasses import dataclass
from enum import Enum, auto
import logging
import queue
import serial
import socket
import threading
import time
from typing import Optional, Union, List


class ModemResponse(Enum):
    """Response types from modem"""
    OK = auto()
    TIMEOUT = auto()
    ERROR = auto()


class SerialState(Enum):
    """States for serial protocol parser"""
    START = auto()
    LENGTH1 = auto()
    LENGTH2 = auto()
    TYPE = auto()
    DATA = auto()


class HardwareType(Enum):
    """Types of MMDVM hardware"""
    UNKNOWN = 0x00
    MMDVM = 0x01
    DVMEGA = 0x02
    MMDVM_ZUMSPOT = 0x03
    MMDVM_HS_HAT = 0x04
    MMDVM_HS_DUAL_HAT = 0x05
    NANO_HOTSPOT = 0x06
    NANO_DV = 0x07
    D2RG_MMDVM_HS = 0x08
    MMDVM_HS = 0x09
    OPENGD77_HS = 0x0A
    SKYBRIDGE = 0x0B


@dataclass
class RingBuffer:
    """Simple ring buffer implementation"""
    def __init__(self, size: int = 3000):
        self.buffer = queue.Queue(size)

    def write(self, data: bytes) -> bool:
        """Write data to buffer"""
        try:
            for byte in data:
                self.buffer.put_nowait(byte)
            return True
        except queue.Full:
            return False

    def read(self, count: int) -> bytes:
        """Read data from buffer"""
        result = bytearray()
        try:
            for _ in range(count):
                result.append(self.buffer.get_nowait())
            return bytes(result)
        except queue.Empty:
            return bytes(result)

    def space(self) -> int:
        """Get available space"""
        return self.buffer.maxsize - self.buffer.qsize()

    def data(self) -> int:
        """Get amount of data available"""
        return self.buffer.qsize()


class Modem:
    """MMDVM modem interface"""

    def __init__(self, port: str, speed: int = 115200, protocol: str = 'uart'):
        """Initialize modem interface
        
        Args:
            port: Serial port or IP address
            speed: Baud rate for serial, or port number for UDP
            protocol: 'uart' or 'udp'
        """
        self.port = port
        self.speed = speed
        self.protocol = protocol
        self.conn: Optional[Union[serial.Serial, socket.socket]] = None
        self.running = False
        self.rx_thread: Optional[threading.Thread] = None

        # Status flags
        self.tx = False
        self.cd = False  # Carrier detect
        self.lockout = False
        self.error = False
        self.mode = 0x00

        # Hardware info
        self.hw_type = HardwareType.UNKNOWN
        self.capabilities1 = 0x00
        self.capabilities2 = 0x00
        self.protocol_version = 0

        # Ring buffers for different modes
        self.rx_dstar = RingBuffer()
        self.tx_dstar = RingBuffer()
        self.rx_dmr1 = RingBuffer()
        self.rx_dmr2 = RingBuffer()
        self.tx_dmr1 = RingBuffer()
        self.tx_dmr2 = RingBuffer()
        self.rx_ysf = RingBuffer()
        self.tx_ysf = RingBuffer()
        self.rx_p25 = RingBuffer()
        self.tx_p25 = RingBuffer()
        self.rx_nxdn = RingBuffer()
        self.tx_nxdn = RingBuffer()
        self.rx_m17 = RingBuffer()
        self.tx_m17 = RingBuffer()
        self.tx_pocsag = RingBuffer()
        self.rx_fm = RingBuffer()
        self.tx_fm = RingBuffer()
        self.rx_ax25 = RingBuffer()
        self.tx_ax25 = RingBuffer()

        # Serial protocol state
        self.state = SerialState.START
        self.buffer = bytearray()
        self.length = 0
        self.offset = 0
        self.type = 0

    def open(self) -> bool:
        """Open connection to modem"""
        try:
            if self.protocol == 'uart':
                self.conn = serial.Serial(
                    port=self.port,
                    baudrate=self.speed,
                    timeout=1
                )
            else:  # UDP
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.conn.bind(('0.0.0.0', 0))  # Random local port
                self.conn.settimeout(1)

            # Start receive thread
            self.running = True
            self.rx_thread = threading.Thread(target=self._rx_loop)
            self.rx_thread.daemon = True
            self.rx_thread.start()

            # Read version info
            if not self._read_version():
                return False

            return True

        except Exception as e:
            logging.error(f"Error opening modem: {e}")
            return False

    def close(self):
        """Close connection to modem"""
        self.running = False
        if self.rx_thread:
            self.rx_thread.join()
        if self.conn:
            self.conn.close()
            self.conn = None

    def _rx_loop(self):
        """Background thread to receive data from modem"""
        while self.running:
            try:
                if self.protocol == 'uart':
                    data = self.conn.read()  # type: ignore
                else:  # UDP
                    data, _ = self.conn.recvfrom(1024)  # type: ignore

                if data:
                    self._process_data(data)

            except Exception as e:
                if self.running:
                    logging.error(f"Error receiving data: {e}")
                time.sleep(0.1)

    def _process_data(self, data: bytes):
        """Process received data according to protocol"""
        for byte in data:
            if self.state == SerialState.START:
                if byte == 0xE0:
                    self.buffer = bytearray([byte])
                    self.length = 0
                    self.offset = 0
                    self.state = SerialState.LENGTH1
            elif self.state == SerialState.LENGTH1:
                self.length = byte << 8
                self.buffer.append(byte)
                self.state = SerialState.LENGTH2
            elif self.state == SerialState.LENGTH2:
                self.length |= byte
                self.buffer.append(byte)
                self.state = SerialState.TYPE
            elif self.state == SerialState.TYPE:
                self.type = byte
                self.buffer.append(byte)
                if self.length > 0:
                    self.state = SerialState.DATA
                else:
                    self._process_frame(self.buffer)
                    self.state = SerialState.START
            elif self.state == SerialState.DATA:
                self.buffer.append(byte)
                self.offset += 1
                if self.offset >= self.length:
                    self._process_frame(self.buffer)
                    self.state = SerialState.START

    def _process_frame(self, frame: bytes):
        """Process a complete frame from the modem"""
        if len(frame) < 4:
            return

        frame_type = frame[3]

        if frame_type == 0x00:  # Get Version
            self.protocol_version = frame[4]
            self.hw_type = HardwareType(frame[5])
            self.capabilities1 = frame[6]
            self.capabilities2 = frame[7] if len(frame) > 7 else 0x00

        elif frame_type == 0x01:  # Get Status
            self.tx = (frame[4] & 0x01) == 0x01
            self.cd = (frame[4] & 0x02) == 0x02
            self.lockout = (frame[4] & 0x04) == 0x04
            self.error = (frame[4] & 0x08) == 0x08

        elif frame_type in (0x20, 0x21):  # D-Star Data
            self.rx_dstar.write(frame[4:])

        elif frame_type in (0x22, 0x23):  # DMR Data
            slot = 1 if frame_type == 0x22 else 2
            if slot == 1:
                self.rx_dmr1.write(frame[4:])
            else:
                self.rx_dmr2.write(frame[4:])

        # Add handlers for other frame types as needed

    def _read_version(self) -> bool:
        """Read version info from modem"""
        cmd = bytes([0xE0, 0x00, 0x01, 0x00])
        if not self._write(cmd):
            return False

        # Wait for response
        start = time.time()
        while time.time() - start < 1.0:
            if self.protocol_version > 0:
                return True
            time.sleep(0.01)

        return False

    def _write(self, data: bytes) -> bool:
        """Write data to modem"""
        try:
            if self.protocol == 'uart':
                return self.conn.write(data) == len(data)  # type: ignore
            else:  # UDP
                addr = (self.port, self.speed)  # port is IP address, speed is port
                return self.conn.sendto(data, addr) == len(data)  # type: ignore
        except Exception as e:
            logging.error(f"Error writing to modem: {e}")
            return False

    def read_mode_data(self, mode: str) -> Optional[bytes]:
        """Read data for specified mode"""
        if mode == 'DSTAR':
            return self.rx_dstar.read(200) if self.rx_dstar.data() > 0 else None
        elif mode == 'DMR1':
            return self.rx_dmr1.read(33) if self.rx_dmr1.data() > 0 else None
        elif mode == 'DMR2':
            return self.rx_dmr2.read(33) if self.rx_dmr2.data() > 0 else None
        elif mode == 'YSF':
            return self.rx_ysf.read(130) if self.rx_ysf.data() > 0 else None
        elif mode == 'P25':
            return self.rx_p25.read(35) if self.rx_p25.data() > 0 else None
        elif mode == 'NXDN':
            return self.rx_nxdn.read(25) if self.rx_nxdn.data() > 0 else None
        elif mode == 'M17':
            return self.rx_m17.read(25) if self.rx_m17.data() > 0 else None
        elif mode == 'FM':
            return self.rx_fm.read(200) if self.rx_fm.data() > 0 else None
        elif mode == 'AX25':
            return self.rx_ax25.read(300) if self.rx_ax25.data() > 0 else None
        return None

    def write_mode_data(self, mode: str, data: bytes) -> bool:
        """Write data for specified mode"""
        if mode == 'DSTAR':
            return self.tx_dstar.write(data)
        elif mode == 'DMR1':
            return self.tx_dmr1.write(data)
        elif mode == 'DMR2':
            return self.tx_dmr2.write(data)
        elif mode == 'YSF':
            return self.tx_ysf.write(data)
        elif mode == 'P25':
            return self.tx_p25.write(data)
        elif mode == 'NXDN':
            return self.tx_nxdn.write(data)
        elif mode == 'M17':
            return self.tx_m17.write(data)
        elif mode == 'POCSAG':
            return self.tx_pocsag.write(data)
        elif mode == 'FM':
            return self.tx_fm.write(data)
        elif mode == 'AX25':
            return self.tx_ax25.write(data)
        return False

    def hasLockout(self) -> bool:
        """Check if modem is locked out"""
        return self.lockout

    def hasError(self) -> bool:
        """Check if modem has error"""
        return self.error

    def set_rf_params(self, rx_freq: int, rx_offset: int, tx_freq: int, tx_offset: int,
                     tx_dc_offset: int, rx_dc_offset: int, rf_level: float, pocsag_freq: int = 0):
        """Set RF parameters
        
        Args:
            rx_freq: Receive frequency in Hz
            rx_offset: Receive offset in Hz
            tx_freq: Transmit frequency in Hz
            tx_offset: Transmit offset in Hz
            tx_dc_offset: Transmit DC offset
            rx_dc_offset: Receive DC offset
            rf_level: RF power level (0.0-100.0)
            pocsag_freq: POCSAG frequency in Hz
        """
        cmd = bytearray([0xE0, 0x00, 0x18, 0x02])
        
        # Add frequencies (4 bytes each, big-endian)
        cmd.extend(rx_freq.to_bytes(4, 'big'))
        cmd.extend(tx_freq.to_bytes(4, 'big'))
        
        # Add offsets (2 bytes each, big-endian, signed)
        cmd.extend(rx_offset.to_bytes(2, 'big', signed=True))
        cmd.extend(tx_offset.to_bytes(2, 'big', signed=True))
        
        # Add DC offsets (1 byte each, signed)
        cmd.append(tx_dc_offset & 0xFF)
        cmd.append(rx_dc_offset & 0xFF)
        
        # Add RF level (1 byte, scaled 0-255)
        cmd.append(int(rf_level * 2.55))
        
        # Add POCSAG frequency if supported
        if self.capabilities1 & 0x10:  # Check if POCSAG is supported
            cmd.extend(pocsag_freq.to_bytes(4, 'big'))
            cmd[2] = 0x1C  # Update length
            
        return self._write(cmd)

    def set_mode_params(self, dstar: bool = False, dmr: bool = False, ysf: bool = False,
                       p25: bool = False, nxdn: bool = False, m17: bool = False,
                       pocsag: bool = False, fm: bool = False, ax25: bool = False):
        """Set enabled modes
        
        Args:
            dstar: Enable D-STAR mode
            dmr: Enable DMR mode
            ysf: Enable System Fusion mode
            p25: Enable P25 mode
            nxdn: Enable NXDN mode
            m17: Enable M17 mode
            pocsag: Enable POCSAG mode
            fm: Enable FM mode
            ax25: Enable AX.25 mode
        """
        cmd = bytearray([0xE0, 0x00, 0x02, 0x03, 0x00])
        
        flags = 0x00
        if dstar: flags |= 0x01
        if dmr: flags |= 0x02
        if ysf: flags |= 0x04
        if p25: flags |= 0x08
        if nxdn: flags |= 0x10
        if m17: flags |= 0x20
        if pocsag: flags |= 0x40
        if fm: flags |= 0x80
        
        cmd[4] = flags
        
        # Add AX.25 if supported
        if self.capabilities2 & 0x01:
            cmd.append(0x01 if ax25 else 0x00)
            cmd[2] = 0x03  # Update length
            
        return self._write(cmd)

    def set_levels(self, rx_level: float, cwid_level: float, dstar_level: float,
                  dmr_level: float, ysf_level: float, p25_level: float,
                  nxdn_level: float, m17_level: float, pocsag_level: float,
                  fm_level: float, ax25_level: float):
        """Set audio levels for different modes (0.0-100.0)"""
        cmd = bytearray([0xE0, 0x00, 0x0B, 0x04])
        
        # Convert levels to bytes (0-255)
        levels = [
            rx_level, cwid_level, dstar_level, dmr_level,
            ysf_level, p25_level, nxdn_level, m17_level,
            pocsag_level, fm_level, ax25_level
        ]
        
        for level in levels:
            cmd.append(int(level * 2.55))
            
        return self._write(cmd)

    def set_dmr_params(self, color_code: int):
        """Set DMR parameters
        
        Args:
            color_code: DMR color code (0-15)
        """
        cmd = bytearray([0xE0, 0x00, 0x02, 0x05])
        cmd.append(color_code & 0x0F)
        return self._write(cmd)

    def set_ysf_params(self, low_deviation: bool, tx_hang: int):
        """Set System Fusion parameters
        
        Args:
            low_deviation: Use low deviation mode
            tx_hang: TX hang time in seconds
        """
        cmd = bytearray([0xE0, 0x00, 0x03, 0x06])
        cmd.append(0x01 if low_deviation else 0x00)
        cmd.append(tx_hang & 0xFF)
        return self._write(cmd)

    def set_p25_params(self, tx_hang: int):
        """Set P25 parameters
        
        Args:
            tx_hang: TX hang time in seconds
        """
        cmd = bytearray([0xE0, 0x00, 0x02, 0x07])
        cmd.append(tx_hang & 0xFF)
        return self._write(cmd)

    def set_nxdn_params(self, tx_hang: int):
        """Set NXDN parameters
        
        Args:
            tx_hang: TX hang time in seconds
        """
        cmd = bytearray([0xE0, 0x00, 0x02, 0x08])
        cmd.append(tx_hang & 0xFF)
        return self._write(cmd)

    def set_m17_params(self, tx_hang: int):
        """Set M17 parameters
        
        Args:
            tx_hang: TX hang time in seconds
        """
        cmd = bytearray([0xE0, 0x00, 0x02, 0x0A])
        cmd.append(tx_hang & 0xFF)
        return self._write(cmd)

    def set_ax25_params(self, rx_twist: int, tx_delay: int, slot_time: int, p_persist: int):
        """Set AX.25 parameters
        
        Args:
            rx_twist: RX twist (-127 to +127)
            tx_delay: TX delay in ms
            slot_time: Slot time in ms
            p_persist: P-persistence value (0-255)
        """
        if not (self.capabilities2 & 0x01):  # Check if AX.25 is supported
            return False
            
        cmd = bytearray([0xE0, 0x00, 0x05, 0x0B])
        cmd.append(rx_twist & 0xFF)
        cmd.append(tx_delay & 0xFF)
        cmd.append(slot_time & 0xFF)
        cmd.append(p_persist & 0xFF)
        return self._write(cmd)

    def set_fm_params(self, callsign: str, callsign_speed: int, callsign_freq: int,
                     callsign_time: int, callsign_holdoff: int, callsign_high_level: float,
                     callsign_low_level: float, callsign_at_start: bool,
                     callsign_at_end: bool, callsign_at_latch: bool):
        """Set FM callsign parameters"""
        cmd = bytearray([0xE0, 0x00])
        
        # Add callsign (up to 8 chars)
        callsign_bytes = callsign[:8].encode()
        cmd.extend([len(callsign_bytes) + 9, 0x0C])  # Type 0x0C
        cmd.extend(callsign_bytes)
        
        # Add parameters
        cmd.append(callsign_speed & 0xFF)
        cmd.append(callsign_freq & 0xFF)
        cmd.append(callsign_time & 0xFF)
        cmd.append(callsign_holdoff & 0xFF)
        cmd.append(int(callsign_high_level * 2.55))
        cmd.append(int(callsign_low_level * 2.55))
        
        flags = 0x00
        if callsign_at_start: flags |= 0x01
        if callsign_at_end: flags |= 0x02
        if callsign_at_latch: flags |= 0x04
        cmd.append(flags)
        
        return self._write(cmd)

    def write_config(self) -> bool:
        """Write current configuration to the modem"""
        cmd = bytearray([0xE0, 0x00, 0x01, 0x09])
        return self._write(cmd)

    def send_cw_id(self, callsign: str) -> bool:
        """Send CW ID using the modem
        
        Args:
            callsign: Callsign to send (max 200 chars)
        
        Returns:
            bool: True if command was sent successfully
        """
        # Limit callsign length to 200 chars
        callsign = callsign[:200]
        
        # Create command buffer
        cmd = bytearray([0xE0])  # Start byte
        cmd.append(len(callsign) + 3)  # Length byte
        cmd.append(0x0E)  # Command type: MMDVM_SEND_CWID
        
        # Add callsign
        cmd.extend(callsign.encode())
        
        return self._write(cmd)