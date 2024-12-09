#!/usr/bin/env python3
"""
Python implementation of MMDVMHost

Copyright (C) 2024 OpenHands
Based on the original MMDVMHost by Jonathan Naylor G4KLX (C) 2015-2021

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any
import os
import time
import logging
from conf import read_config


class Mode(Enum):
    """Operating modes for the MMDVM"""
    IDLE = auto()
    DSTAR = auto()
    DMR = auto()
    YSF = auto()
    P25 = auto()
    NXDN = auto()
    M17 = auto()
    POCSAG = auto()
    FM = auto()
    AX25 = auto()
    LOCKOUT = auto()
    ERROR = auto()


@dataclass
class Timer:
    """Simple timer implementation"""
    running: bool = False
    timeout: float = 0.0
    start_time: float = 0.0

    def start(self):
        """Start the timer"""
        self.running = True
        self.start_time = time.time()

    def stop(self):
        """Stop the timer"""
        self.running = False

    def isRunning(self) -> bool:
        """Check if timer is running"""
        return self.running

    def setTimeout(self, timeout: float):
        """Set timeout and start timer"""
        self.timeout = timeout
        self.start()

    def hasExpired(self) -> bool:
        """Check if timer has expired"""
        if not self.running:
            return False
        return (time.time() - self.start_time) >= self.timeout


class MMDVMHost:
    """Main MMDVMHost class that manages the MMDVM modem and networks"""

    def __init__(self, conf_file: str):
        """Initialize MMDVMHost with configuration file path"""
        self.config = read_config(conf_file)
        self.mode = Mode.IDLE
        self.modem = None
        self.networks: Dict[Mode, Any] = {}
        self.mode_timer = Timer()
        self.dmr_tx_timer = Timer()
        self.cw_id_timer = Timer()
        self.killed = False

    def run(self) -> int:
        """Main run loop of MMDVMHost"""
        # Initialize logging
        log_level = self.config.getint('Log', 'DisplayLevel', fallback=0)
        logging.basicConfig(level=log_level * 10)  # 0=NOTSET, 1=DEBUG, 2=INFO, etc.
        logging.info("MMDVMHost is starting")

        # Create modem
        if not self.create_modem():
            logging.error("Unable to create modem")
            return 1

        # Create networks for enabled modes
        for mode in Mode:
            if mode in (Mode.LOCKOUT, Mode.ERROR, Mode.IDLE):
                continue
            section = mode.name.replace('_', ' ')
            if self.config.getboolean(section, 'Enable', fallback=False):
                if not self.create_network(mode):
                    logging.error(f"Unable to create {mode.name} network")
                    return 1

        # Main loop
        while not self.killed:
            # Check modem status
            if self.modem.hasLockout() and self.mode != Mode.LOCKOUT:
                self.set_mode(Mode.LOCKOUT)
            elif not self.modem.hasLockout() and self.mode == Mode.LOCKOUT:
                self.set_mode(Mode.IDLE)

            if self.modem.hasError() and self.mode != Mode.ERROR:
                self.set_mode(Mode.ERROR)
            elif not self.modem.hasError() and self.mode == Mode.ERROR:
                self.set_mode(Mode.IDLE)

            # Process data from modem
            self.process_modem_data()

            # Check timers
            if self.mode_timer.hasExpired():
                self.set_mode(Mode.IDLE)

            # Sleep a bit to prevent busy waiting
            time.sleep(0.001)  # 1ms

        return 0

    def create_modem(self) -> bool:
        """Create and initialize the MMDVM modem"""
        from modem import Modem  # Import here to avoid circular imports
        
        try:
            protocol = self.config.get('Modem', 'Protocol')
            if protocol == 'uart':
                port = self.config.get('Modem', 'UARTPort')
                speed = self.config.getint('Modem', 'UARTSpeed')
                self.modem = Modem(port, speed)
            elif protocol == 'udp':
                address = self.config.get('Modem', 'ModemAddress')
                port = self.config.getint('Modem', 'ModemPort')
                self.modem = Modem(address, port, protocol='udp')
            else:
                logging.error(f"Unknown modem protocol: {protocol}")
                return False

            return self.modem.open()
        except Exception as e:
            logging.error(f"Error creating modem: {e}")
            return False

    def create_network(self, mode: Mode) -> bool:
        """Create and initialize network connection for given mode"""
        try:
            section = f"{mode.name.replace('_', ' ')} Network"
            if not self.config.getboolean(section, 'Enable', fallback=False):
                return True  # Not enabled is not an error

            # Import the appropriate network class
            module = __import__(f"{mode.name.lower()}_network")
            network_class = getattr(module, f"{mode.name}Network")

            # Create network instance
            self.networks[mode] = network_class(self.config)
            return self.networks[mode].open()
        except Exception as e:
            logging.error(f"Error creating {mode.name} network: {e}")
            return False

    def process_modem_data(self):
        """Process data received from the modem"""
        # Read data from modem for each mode
        for mode in Mode:
            if mode in (Mode.LOCKOUT, Mode.ERROR, Mode.IDLE):
                continue
            if mode not in self.networks:
                continue

            data = self.modem.read_mode_data(mode)
            if data:
                if self.mode == Mode.IDLE:
                    # New transmission, switch to this mode
                    if self.networks[mode].write_modem(data):
                        hang_time = self.config.getint(mode.name, 'RFModeHang', fallback=10)
                        self.mode_timer.setTimeout(hang_time)
                        self.set_mode(mode)
                elif self.mode == mode:
                    # Continuation of current transmission
                    if self.networks[mode].write_modem(data):
                        self.mode_timer.start()
                else:
                    logging.warning(f"{mode.name} data received when in {self.mode.name} mode")

    def set_mode(self, mode: Mode):
        """Set the current operating mode"""
        if mode == self.mode:
            return

        logging.info(f"Mode change from {self.mode.name} to {mode.name}")
        self.mode = mode

        # Stop all network activity when going idle
        if mode == Mode.IDLE:
            for network in self.networks.values():
                network.stop()
            self.mode_timer.stop()