#!/usr/bin/env python3
"""
Configuration handler for MMDVMHost
"""

from configparser import ConfigParser
import os

def read_config(config_file: str) -> ConfigParser:
    """Read and parse the configuration file"""
    config = ConfigParser(inline_comment_prefixes=('#', ';'))
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' does not exist")
    config.read(config_file)
    return config