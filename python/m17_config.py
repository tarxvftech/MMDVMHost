#!/usr/bin/env python3
"""
M17 protocol configuration
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class M17Config:
    """M17 protocol configuration"""
    # Timing constants
    RADIO_SYMBOL_LENGTH: ClassVar[int] = 5  # At 24 kHz sample rate

    # Frame sizes
    FRAME_LENGTH_BITS: ClassVar[int] = 384
    FRAME_LENGTH_BYTES: ClassVar[int] = FRAME_LENGTH_BITS // 8

    # Sync bytes
    LINK_SETUP_SYNC: ClassVar[bytes] = bytes([0x55, 0xF7])
    STREAM_SYNC: ClassVar[bytes] = bytes([0xFF, 0x5D])
    EOT_SYNC: ClassVar[bytes] = bytes([0x55, 0x5D])

    # Sync lengths
    SYNC_LENGTH_BITS: ClassVar[int] = 16
    SYNC_LENGTH_BYTES: ClassVar[int] = SYNC_LENGTH_BITS // 8

    # LSF sizes
    LSF_LENGTH_BITS: ClassVar[int] = 240
    LSF_LENGTH_BYTES: ClassVar[int] = LSF_LENGTH_BITS // 8
    LSF_FRAGMENT_LENGTH_BITS: ClassVar[int] = LSF_LENGTH_BITS // 6
    LSF_FRAGMENT_LENGTH_BYTES: ClassVar[int] = LSF_FRAGMENT_LENGTH_BITS // 8

    # LICH sizes
    LICH_FRAGMENT_LENGTH_BITS: ClassVar[int] = LSF_FRAGMENT_LENGTH_BITS + 8
    LICH_FRAGMENT_LENGTH_BYTES: ClassVar[int] = LICH_FRAGMENT_LENGTH_BITS // 8

    # FEC lengths
    LSF_FRAGMENT_FEC_LENGTH_BITS: ClassVar[int] = LSF_FRAGMENT_LENGTH_BITS * 2
    LSF_FRAGMENT_FEC_LENGTH_BYTES: ClassVar[int] = LSF_FRAGMENT_FEC_LENGTH_BITS // 8
    LICH_FRAGMENT_FEC_LENGTH_BITS: ClassVar[int] = LICH_FRAGMENT_LENGTH_BITS * 2
    LICH_FRAGMENT_FEC_LENGTH_BYTES: ClassVar[int] = LICH_FRAGMENT_FEC_LENGTH_BITS // 8

    # Payload sizes
    PAYLOAD_LENGTH_BITS: ClassVar[int] = 128
    PAYLOAD_LENGTH_BYTES: ClassVar[int] = PAYLOAD_LENGTH_BITS // 8

    # Metadata sizes
    NULL_NONCE: ClassVar[bytes] = bytes([0x00] * 14)
    META_LENGTH_BITS: ClassVar[int] = 112
    META_LENGTH_BYTES: ClassVar[int] = META_LENGTH_BITS // 8

    # Frame number sizes
    FN_LENGTH_BITS: ClassVar[int] = 16
    FN_LENGTH_BYTES: ClassVar[int] = FN_LENGTH_BITS // 8

    # CRC sizes
    CRC_LENGTH_BITS: ClassVar[int] = 16
    CRC_LENGTH_BYTES: ClassVar[int] = CRC_LENGTH_BITS // 8

    # Silence frames
    SILENCE_3200: ClassVar[bytes] = bytes([0x01, 0x00, 0x09, 0x43, 0x9C, 0xE4, 0x21, 0x08])
    SILENCE_1600: ClassVar[bytes] = bytes([0x0C, 0x41, 0x09, 0x03, 0x0C, 0x41, 0x09, 0x03])

    # Validation constants
    MAX_CALLSIGN_LENGTH: ClassVar[int] = 6
    MIN_FRAME_LENGTH: ClassVar[int] = SYNC_LENGTH_BYTES + 4  # Sync + minimal payload
    MAX_FRAME_LENGTH: ClassVar[int] = FRAME_LENGTH_BYTES
    NUM_LICH_FRAGMENTS: ClassVar[int] = 6