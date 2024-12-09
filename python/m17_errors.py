#!/usr/bin/env python3
"""
M17 protocol error types
"""

class M17Error(Exception):
    """Base class for M17 exceptions"""
    pass


class CRCError(M17Error):
    """CRC check failed"""
    pass


class LSFError(M17Error):
    """Base class for LSF errors"""
    pass


class LSFDecodeError(LSFError):
    """Error decoding Link Setup Frame"""
    pass


class LSFEncodeError(LSFError):
    """Error encoding Link Setup Frame"""
    pass


class StreamError(M17Error):
    """Base class for stream frame errors"""
    pass


class StreamDecodeError(StreamError):
    """Error decoding stream frame"""
    pass


class StreamEncodeError(StreamError):
    """Error encoding stream frame"""
    pass


class LICHError(M17Error):
    """Base class for LICH errors"""
    pass


class FragmentError(LICHError):
    """Invalid LICH fragment"""
    pass