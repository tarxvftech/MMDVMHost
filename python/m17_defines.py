#!/usr/bin/env python3
"""
M17 protocol definitions
"""

from enum import IntEnum

# Timing constants
RADIO_SYMBOL_LENGTH = 5  # At 24 kHz sample rate

# Frame sizes
FRAME_LENGTH_BITS = 384
FRAME_LENGTH_BYTES = FRAME_LENGTH_BITS // 8

# Sync bytes
LINK_SETUP_SYNC = bytes([0x55, 0xF7])
STREAM_SYNC = bytes([0xFF, 0x5D])
EOT_SYNC = bytes([0x55, 0x5D])

# Sync lengths
SYNC_LENGTH_BITS = 16
SYNC_LENGTH_BYTES = SYNC_LENGTH_BITS // 8

# LSF (Link Setup Frame) sizes
LSF_LENGTH_BITS = 240
LSF_LENGTH_BYTES = LSF_LENGTH_BITS // 8
LSF_FRAGMENT_LENGTH_BITS = LSF_LENGTH_BITS // 6
LSF_FRAGMENT_LENGTH_BYTES = LSF_FRAGMENT_LENGTH_BITS // 8

# LICH (Link Information Channel) sizes
LICH_FRAGMENT_LENGTH_BITS = LSF_FRAGMENT_LENGTH_BITS + 8
LICH_FRAGMENT_LENGTH_BYTES = LICH_FRAGMENT_LENGTH_BITS // 8

# FEC lengths
LSF_FRAGMENT_FEC_LENGTH_BITS = LSF_FRAGMENT_LENGTH_BITS * 2
LSF_FRAGMENT_FEC_LENGTH_BYTES = LSF_FRAGMENT_FEC_LENGTH_BITS // 8
LICH_FRAGMENT_FEC_LENGTH_BITS = LICH_FRAGMENT_LENGTH_BITS * 2
LICH_FRAGMENT_FEC_LENGTH_BYTES = LICH_FRAGMENT_FEC_LENGTH_BITS // 8

# Payload sizes
PAYLOAD_LENGTH_BITS = 128
PAYLOAD_LENGTH_BYTES = PAYLOAD_LENGTH_BITS // 8

# Metadata sizes
NULL_NONCE = bytes([0x00] * 14)
META_LENGTH_BITS = 112
META_LENGTH_BYTES = META_LENGTH_BITS // 8

# Frame number sizes
FN_LENGTH_BITS = 16
FN_LENGTH_BYTES = FN_LENGTH_BITS // 8

# CRC sizes
CRC_LENGTH_BITS = 16
CRC_LENGTH_BYTES = CRC_LENGTH_BITS // 8

# Silence frames
SILENCE_3200 = bytes([0x01, 0x00, 0x09, 0x43, 0x9C, 0xE4, 0x21, 0x08])
SILENCE_1600 = bytes([0x0C, 0x41, 0x09, 0x03, 0x0C, 0x41, 0x09, 0x03])


class PacketType(IntEnum):
    """M17 packet types"""
    PACKET = 0
    STREAM = 1


class DataType(IntEnum):
    """M17 data types"""
    DATA = 0x01
    VOICE = 0x02
    VOICE_DATA = 0x03


class EncryptionType(IntEnum):
    """M17 encryption types"""
    NONE = 0x00
    AES = 0x01
    SCRAMBLE = 0x02


class EncryptionSubType(IntEnum):
    """M17 encryption subtypes"""
    TEXT = 0x00
    GPS = 0x01
    CALLSIGNS = 0x02