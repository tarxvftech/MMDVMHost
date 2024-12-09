#!/usr/bin/env python3
"""
M17 protocol controller
"""

import logging
import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Optional

import struct
from m17_defines import *
from m17_network import M17Network
from m17_lsf import LSF, StreamFrame, LICHReassembler


@dataclass
class M17Control:
    """M17 protocol controller"""
    callsign: str
    can: int
    self_only: bool
    allow_encryption: bool
    tx_hang: int
    network: Optional[M17Network] = None
    
    # Internal state
    rf_state: str = 'NONE'
    net_state: str = 'NONE'
    rf_timeout: float = 0
    net_timeout: float = 0
    rf_frames: int = 0
    net_frames: int = 0
    rf_bits: int = 0
    net_bits: int = 0
    rf_errs: int = 0
    net_errs: int = 0
    rf_last_frame: int = 0
    net_last_frame: int = 0
    tx_watchdog: int = 0
    rf_lich: LICHReassembler = field(default_factory=LICHReassembler)
    net_lich: LICHReassembler = field(default_factory=LICHReassembler)
    
    # Buffers
    rf_data: Queue = field(default_factory=lambda: Queue(maxsize=1))
    net_data: Queue = field(default_factory=lambda: Queue(maxsize=1))

    def write_rf_data(self, data: bytes) -> bool:
        """Write RF data to controller"""
        if len(data) != FRAME_LENGTH_BYTES:
            return False
            
        try:
            self.rf_data.put_nowait(data)
            return True
        except:
            return False

    def write_network_data(self, data: bytes) -> bool:
        """Write network data to controller"""
        if len(data) != FRAME_LENGTH_BYTES:
            return False
            
        try:
            self.net_data.put_nowait(data)
            return True
        except:
            return False

    def process_rf_data(self):
        """Process RF data"""
        try:
            data = self.rf_data.get_nowait()
        except:
            return

        # Extract sync from frame
        sync = data[0:SYNC_LENGTH_BYTES]

        if sync == LINK_SETUP_SYNC:
            # Handle link setup frame
            self._handle_rf_link_setup(data)
            
        elif sync == STREAM_SYNC:
            # Handle stream frame
            self._handle_rf_stream(data)
            
        elif sync == EOT_SYNC:
            # Handle end of transmission
            self._handle_rf_eot()

    def process_network_data(self):
        """Process network data"""
        try:
            data = self.net_data.get_nowait()
        except:
            return

        # Extract sync from frame
        sync = data[0:SYNC_LENGTH_BYTES]

        if sync == LINK_SETUP_SYNC:
            # Handle link setup frame
            self._handle_net_link_setup(data)
            
        elif sync == STREAM_SYNC:
            # Handle stream frame
            self._handle_net_stream(data)
            
        elif sync == EOT_SYNC:
            # Handle end of transmission
            self._handle_net_eot()

    def clock(self, ms: int):
        """Clock tick handler"""
        # Process timeouts
        now = time.time()
        
        if self.rf_state == 'PROCESS' and now >= self.rf_timeout:
            self._handle_rf_timeout()
            
        if self.net_state == 'PROCESS' and now >= self.net_timeout:
            self._handle_net_timeout()
            
        # Process watchdog
        if self.tx_watchdog > 0:
            self.tx_watchdog -= ms
            if self.tx_watchdog <= 0:
                logging.warning("M17 transmit watchdog triggered")
                self.rf_state = 'NONE'
                self.net_state = 'NONE'

    def _handle_rf_link_setup(self, data: bytes):
        """Handle RF link setup frame"""
        if self.rf_state != 'NONE':
            return
            
        # Extract and validate LSF
        lsf = LSF.decode(data[SYNC_LENGTH_BYTES:])
        if not lsf:
            logging.error("Failed to decode RF LSF")
            return
            
        # Check if we should process this transmission
        if self.self_only and lsf.dst_callsign != self.callsign:
            return
            
        # Check encryption
        if lsf.encryption_type != EncryptionType.NONE and not self.allow_encryption:
            logging.warning("Encrypted transmission received but encryption not allowed")
            return
            
        # Start processing
        self.rf_state = 'PROCESS'
        self.rf_timeout = time.time() + self.tx_hang
        self.rf_frames = 0
        self.rf_bits = 0
        self.rf_errs = 0
        self.rf_lich = LICHReassembler()
        
        logging.info(f"M17 RF transmission from {lsf.src_callsign} to {lsf.dst_callsign}")
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(data)

    def _handle_rf_stream(self, data: bytes):
        """Handle RF stream frame"""
        if self.rf_state != 'PROCESS':
            return
            
        # Decode stream frame
        frame = StreamFrame.decode(data)
        if not frame:
            logging.error("Failed to decode RF stream frame")
            return
            
        # Process LICH fragment if present
        if frame.lich_fragment:
            lsf = self.rf_lich.add_fragment(frame.lich_fragment, frame.frame_number)
            if lsf:
                # Validate LSF matches current transmission
                # TODO: Add validation
                pass
            
        # Update statistics
        self.rf_frames += 1
        self.rf_bits += len(frame.payload) * 8
        self.rf_last_frame = frame.frame_number
        
        # Reset timeout
        self.rf_timeout = time.time() + self.tx_hang
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(data)

    def _handle_rf_eot(self):
        """Handle RF end of transmission"""
        if self.rf_state != 'PROCESS':
            return
            
        # Log statistics
        ber = 0.0 if self.rf_bits == 0 else (self.rf_errs * 100.0) / self.rf_bits
        logging.info(f"M17 RF end of transmission: {self.rf_frames} frames, BER: {ber:.1f}%")
        
        self.rf_state = 'NONE'
        self.rf_lich.reset()
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(EOT_SYNC)

    def _handle_rf_timeout(self):
        """Handle RF timeout"""
        if self.rf_state != 'PROCESS':
            return
            
        logging.warning("M17 RF timeout")
        self.rf_state = 'NONE'
        self.rf_lich.reset()
        
        # Forward EOT to network
        if self.network and self.network.is_connected():
            self.network.write(EOT_SYNC)

    def _handle_net_link_setup(self, data: bytes):
        """Handle network link setup frame"""
        if self.net_state != 'NONE':
            return
            
        # Extract and validate LSF
        lsf = LSF.decode(data[SYNC_LENGTH_BYTES:])
        if not lsf:
            logging.error("Failed to decode network LSF")
            return
            
        # Check if we should process this transmission
        if self.self_only and lsf.dst_callsign != self.callsign:
            return
            
        # Check encryption
        if lsf.encryption_type != EncryptionType.NONE and not self.allow_encryption:
            logging.warning("Encrypted transmission received but encryption not allowed")
            return
            
        # Start processing
        self.net_state = 'PROCESS'
        self.net_timeout = time.time() + self.tx_hang
        self.net_frames = 0
        self.net_bits = 0
        self.net_errs = 0
        self.net_lich = LICHReassembler()
        
        logging.info(f"M17 network transmission from {lsf.src_callsign} to {lsf.dst_callsign}")

    def _handle_net_stream(self, data: bytes):
        """Handle network stream frame"""
        if self.net_state != 'PROCESS':
            return
            
        # Decode stream frame
        frame = StreamFrame.decode(data)
        if not frame:
            logging.error("Failed to decode network stream frame")
            return
            
        # Process LICH fragment if present
        if frame.lich_fragment:
            lsf = self.net_lich.add_fragment(frame.lich_fragment, frame.frame_number)
            if lsf:
                # Validate LSF matches current transmission
                # TODO: Add validation
                pass
            
        # Update statistics
        self.net_frames += 1
        self.net_bits += len(frame.payload) * 8
        self.net_last_frame = frame.frame_number
        
        # Reset timeout
        self.net_timeout = time.time() + self.tx_hang

    def _handle_net_eot(self):
        """Handle network end of transmission"""
        if self.net_state != 'PROCESS':
            return
            
        # Log statistics
        ber = 0.0 if self.net_bits == 0 else (self.net_errs * 100.0) / self.net_bits
        logging.info(f"M17 network end of transmission: {self.net_frames} frames, BER: {ber:.1f}%")
        
        self.net_state = 'NONE'
        self.net_lich.reset()

    def _handle_net_timeout(self):
        """Handle network timeout"""
        if self.net_state != 'PROCESS':
            return
            
        logging.warning("M17 network timeout")
        self.net_state = 'NONE'
        self.net_lich.reset()