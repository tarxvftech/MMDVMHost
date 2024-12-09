#!/usr/bin/env python3
"""
M17 CRC implementation using Python's zlib.crc32
"""

from typing import Union
import zlib

from m17_errors import CRCError


def create_crc16(data: Union[bytes, bytearray]) -> int:
    """Calculate CRC-16 for given data
    
    Args:
        data: Input data
        
    Returns:
        16-bit CRC value
        
    Raises:
        TypeError: If data is not bytes or bytearray
        ValueError: If data is empty
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"Expected bytes or bytearray, got {type(data)}")
        
    if not data:
        raise ValueError("Empty data")
        
    return zlib.crc32(data) & 0xFFFF


def check_crc16(data: Union[bytes, bytearray]) -> bool:
    """Check if data has valid CRC-16
    
    Args:
        data: Data with CRC bytes at end
        
    Returns:
        True if CRC is valid
        
    Raises:
        TypeError: If data is not bytes or bytearray
        ValueError: If data is too short
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"Expected bytes or bytearray, got {type(data)}")
        
    if len(data) < 3:
        raise ValueError(f"Data too short for CRC: {len(data)} < 3")
        
    try:
        return create_crc16(data[:-2]) == int.from_bytes(data[-2:], 'big')
    except Exception as e:
        raise CRCError(f"CRC check failed: {e}")


def encode_crc16(data: Union[bytes, bytearray]) -> bytes:
    """Add CRC-16 to data
    
    Args:
        data: Input data
        
    Returns:
        Data with CRC bytes appended
        
    Raises:
        TypeError: If data is not bytes or bytearray
        ValueError: If data is empty
        CRCError: If CRC calculation fails
    """
    try:
        crc = create_crc16(data)
        result = bytes(data) + crc.to_bytes(2, 'big')
        
        # Verify the CRC
        if not check_crc16(result):
            raise CRCError("CRC verification failed")
            
        return result
    except (TypeError, ValueError) as e:
        raise e
    except Exception as e:
        raise CRCError(f"CRC encoding failed: {e}")