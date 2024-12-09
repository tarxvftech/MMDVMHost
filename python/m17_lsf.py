#!/usr/bin/env python3
"""
M17 Link Setup Frame (LSF) handler
"""

import logging
import struct
from dataclasses import dataclass, field
from threading import Lock
from typing import List, Optional, Tuple

from m17_config import M17Config
from m17_crc import check_crc16, encode_crc16
from m17_defines import PacketType, DataType, EncryptionType, EncryptionSubType
from m17_errors import LSFDecodeError, LSFEncodeError, FragmentError


@dataclass
class LSF:
    """M17 Link Setup Frame"""
    dst_callsign: str = ""
    src_callsign: str = ""
    can: int = 0
    packet_type: PacketType = PacketType.STREAM
    data_type: DataType = DataType.VOICE
    encryption_type: EncryptionType = EncryptionType.NONE
    encryption_subtype: EncryptionSubType = EncryptionSubType.TEXT
    nonce: bytes = field(default_factory=lambda: NULL_NONCE)

    @classmethod
    def decode(cls, data: bytes) -> 'LSF':
        """Decode LSF from bytes
        
        Args:
            data: LSF data with CRC
            
        Returns:
            Decoded LSF object
            
        Raises:
            TypeError: If data is not bytes
            ValueError: If data length is invalid
            LSFDecodeError: If LSF decoding fails
        """
        if not isinstance(data, bytes):
            raise TypeError(f"Expected bytes, got {type(data)}")
            
        if len(data) < M17Config.LSF_LENGTH_BYTES:
            raise ValueError(
                f"Data too short: {len(data)} < {M17Config.LSF_LENGTH_BYTES}"
            )

        try:
            # Check CRC
            if not check_crc16(data):
                raise LSFDecodeError("CRC check failed")

            # Extract fields (excluding CRC)
            try:
                dst = cls._decode_callsign(data[0:6])
                src = cls._decode_callsign(data[6:12])
            except UnicodeDecodeError as e:
                raise LSFDecodeError(f"Invalid callsign encoding: {e}")
            
            # Extract type fields
            try:
                type_byte = data[12]
                packet_type = PacketType(type_byte & 0x01)
                data_type = DataType((type_byte >> 1) & 0x03)
                encryption_type = EncryptionType((type_byte >> 3) & 0x03)
                encryption_subtype = EncryptionSubType((type_byte >> 5) & 0x03)
            except ValueError as e:
                raise LSFDecodeError(f"Invalid type field: {e}")
            
            # Extract CAN (Channel Access Number)
            try:
                can = int.from_bytes(data[13:15], 'big')
            except Exception as e:
                raise LSFDecodeError(f"Invalid CAN field: {e}")
            
            # Extract nonce if present
            nonce = data[15:29] if len(data) >= 29 else M17Config.NULL_NONCE
            
            return cls(
                dst_callsign=dst,
                src_callsign=src,
                can=can,
                packet_type=packet_type,
                data_type=data_type,
                encryption_type=encryption_type,
                encryption_subtype=encryption_subtype,
                nonce=nonce
            )
            
        except (LSFDecodeError, TypeError, ValueError) as e:
            raise e
        except Exception as e:
            raise LSFDecodeError(f"Unexpected error: {e}")

    def encode(self) -> bytes:
        """Encode LSF to bytes
        
        Returns:
            LSF data with CRC
            
        Raises:
            LSFEncodeError: If encoding fails
        """
        try:
            # Validate callsigns
            if not self.dst_callsign or len(self.dst_callsign) > M17Config.MAX_CALLSIGN_LENGTH:
                raise ValueError(f"Invalid destination callsign: {self.dst_callsign}")
            if not self.src_callsign or len(self.src_callsign) > M17Config.MAX_CALLSIGN_LENGTH:
                raise ValueError(f"Invalid source callsign: {self.src_callsign}")
                
            # Validate CAN
            if not 0 <= self.can <= 0xFFFF:
                raise ValueError(f"Invalid CAN value: {self.can}")
                
            # Validate nonce
            if len(self.nonce) != len(M17Config.NULL_NONCE):
                raise ValueError(f"Invalid nonce length: {len(self.nonce)}")
                
            # Build frame
            frame = (
                self._encode_callsign(self.dst_callsign) +
                self._encode_callsign(self.src_callsign) +
                bytes([
                    self.packet_type.value |
                    (self.data_type.value << 1) |
                    (self.encryption_type.value << 3) |
                    (self.encryption_subtype.value << 5)
                ]) +
                self.can.to_bytes(2, 'big') +
                self.nonce
            )
            
            # Add padding and CRC
            frame = frame.ljust(M17Config.LSF_LENGTH_BYTES - M17Config.CRC_LENGTH_BYTES, b'\x00')
            return encode_crc16(frame)
            
        except ValueError as e:
            raise LSFEncodeError(str(e))
        except Exception as e:
            raise LSFEncodeError(f"Failed to encode LSF: {e}")

    @staticmethod
    def _decode_callsign(data: bytes) -> str:
        """Decode callsign from bytes"""
        return data.rstrip(b'\x00').decode('ascii', errors='ignore').strip()

    @staticmethod
    def _encode_callsign(callsign: str) -> bytes:
        """Encode callsign to bytes"""
        return callsign.encode('ascii')[:6].ljust(6, b'\x00')


@dataclass
class StreamFrame:
    """M17 Stream Frame"""
    frame_number: int = 0
    payload: bytes = field(default_factory=bytes)
    lich_fragment: Optional[bytes] = None
    is_last: bool = False

    @classmethod
    def decode(cls, data: bytes) -> 'StreamFrame':
        """Decode stream frame from bytes
        
        Args:
            data: Stream frame data with CRC
            
        Returns:
            Decoded StreamFrame object
            
        Raises:
            TypeError: If data is not bytes
            ValueError: If data length is invalid
            StreamDecodeError: If frame decoding fails
        """
        if not isinstance(data, bytes):
            raise TypeError(f"Expected bytes, got {type(data)}")
            
        if len(data) < M17Config.MIN_FRAME_LENGTH:
            raise ValueError(
                f"Data too short: {len(data)} < {M17Config.MIN_FRAME_LENGTH}"
            )
            
        if len(data) > M17Config.MAX_FRAME_LENGTH:
            raise ValueError(
                f"Data too long: {len(data)} > {M17Config.MAX_FRAME_LENGTH}"
            )

        try:
            # Check CRC
            if not check_crc16(data):
                raise StreamDecodeError("CRC check failed")

            # Check sync bytes
            if data[:M17Config.SYNC_LENGTH_BYTES] != M17Config.STREAM_SYNC:
                raise StreamDecodeError("Invalid sync bytes")

            # Extract frame number
            try:
                fn = int.from_bytes(
                    data[M17Config.SYNC_LENGTH_BYTES:M17Config.SYNC_LENGTH_BYTES+2],
                    'big'
                )
                is_last = bool(fn & 0x8000)
                frame_number = fn & 0x7FFF
            except Exception as e:
                raise StreamDecodeError(f"Invalid frame number: {e}")
            
            # Extract LICH fragment and payload
            try:
                lich = (
                    data[M17Config.SYNC_LENGTH_BYTES+2:M17Config.SYNC_LENGTH_BYTES+6]
                    if frame_number < M17Config.NUM_LICH_FRAGMENTS else None
                )
                payload = data[
                    M17Config.SYNC_LENGTH_BYTES+6:
                    M17Config.FRAME_LENGTH_BYTES-M17Config.CRC_LENGTH_BYTES
                ]
            except Exception as e:
                raise StreamDecodeError(f"Invalid frame data: {e}")
            
            return cls(frame_number, payload, lich, is_last)
            
        except (StreamDecodeError, TypeError, ValueError) as e:
            raise e
        except Exception as e:
            raise StreamDecodeError(f"Unexpected error: {e}")

    def encode(self) -> bytes:
        """Encode stream frame to bytes
        
        Returns:
            Stream frame data with CRC
            
        Raises:
            StreamEncodeError: If encoding fails
        """
        try:
            # Validate frame number
            if not 0 <= self.frame_number <= 0x7FFF:
                raise ValueError(f"Invalid frame number: {self.frame_number}")
                
            # Validate LICH fragment
            if (self.lich_fragment is not None and 
                len(self.lich_fragment) != M17Config.LSF_FRAGMENT_LENGTH_BYTES):
                raise ValueError(
                    f"Invalid LICH fragment size: {len(self.lich_fragment)}"
                )
                
            # Validate payload
            if len(self.payload) > M17Config.PAYLOAD_LENGTH_BYTES:
                raise ValueError(
                    f"Payload too long: {len(self.payload)} > "
                    f"{M17Config.PAYLOAD_LENGTH_BYTES}"
                )
                
            # Build frame
            frame = (
                M17Config.STREAM_SYNC +
                ((self.frame_number | (0x8000 if self.is_last else 0))
                 .to_bytes(2, 'big')) +
                (self.lich_fragment or bytes(4)) +
                self.payload
            )
            
            # Add padding and CRC
            frame = frame.ljust(
                M17Config.FRAME_LENGTH_BYTES - M17Config.CRC_LENGTH_BYTES,
                b'\x00'
            )
            return encode_crc16(frame)
            
        except ValueError as e:
            raise StreamEncodeError(str(e))
        except Exception as e:
            raise StreamEncodeError(f"Failed to encode stream frame: {e}")


class LICHReassembler:
    """LICH fragment reassembler with thread safety"""
    def __init__(self):
        self._fragments: List[Optional[bytes]] = [None] * M17Config.NUM_LICH_FRAGMENTS
        self._lock = Lock()

    def add_fragment(self, fragment: bytes, index: int) -> Optional[LSF]:
        """Add a LICH fragment and try to reassemble
        
        Args:
            fragment: LICH fragment data
            index: Fragment index (0-5)
            
        Returns:
            Reassembled LSF if all fragments present, None otherwise
            
        Raises:
            TypeError: If fragment is not bytes
            ValueError: If fragment size or index invalid
            FragmentError: If fragment reassembly fails
        """
        if not isinstance(fragment, bytes):
            raise TypeError(f"Expected bytes, got {type(fragment)}")
            
        if len(fragment) != M17Config.LSF_FRAGMENT_LENGTH_BYTES:
            raise ValueError(
                f"Invalid fragment size: {len(fragment)} != "
                f"{M17Config.LSF_FRAGMENT_LENGTH_BYTES}"
            )
            
        if not 0 <= index < M17Config.NUM_LICH_FRAGMENTS:
            raise ValueError(
                f"Invalid fragment index: {index} not in "
                f"0-{M17Config.NUM_LICH_FRAGMENTS-1}"
            )
            
        with self._lock:
            self._fragments[index] = fragment
            
            # Try to reassemble if we have all fragments
            if all(f is not None for f in self._fragments):
                try:
                    return LSF.decode(b''.join(self._fragments))
                except Exception as e:
                    raise FragmentError(f"Failed to reassemble LSF: {e}")
                    
        return None

    def reset(self):
        """Reset reassembler state"""
        with self._lock:
            self._fragments = [None] * M17Config.NUM_LICH_FRAGMENTS

    @property
    def is_complete(self) -> bool:
        """Check if all fragments are present"""
        with self._lock:
            return all(f is not None for f in self._fragments)