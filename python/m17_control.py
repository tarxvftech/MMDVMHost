#!/usr/bin/env python3
"""
M17 protocol controller
"""

import logging
import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Optional

from m17_defines import *
from m17_network import M17Network


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
    rf_state = 'NONE'
    net_state = 'NONE'
    rf_timeout = 0
    net_timeout = 0
    rf_frames = 0
    net_frames = 0
    rf_bits = 0
    net_bits = 0
    rf_errs = 0
    net_errs = 0
    rf_last_frame = 0
    net_last_frame = 0
    tx_watchdog = 0
    
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
            
        # TODO: Extract and validate LSF fields
        
        self.rf_state = 'PROCESS'
        self.rf_timeout = time.time() + self.tx_hang
        self.rf_frames = 0
        self.rf_bits = 0
        self.rf_errs = 0
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(data)

    def _handle_rf_stream(self, data: bytes):
        """Handle RF stream frame"""
        if self.rf_state != 'PROCESS':
            return
            
        # TODO: Extract and validate stream fields
        
        self.rf_frames += 1
        self.rf_timeout = time.time() + self.tx_hang
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(data)

    def _handle_rf_eot(self):
        """Handle RF end of transmission"""
        if self.rf_state != 'PROCESS':
            return
            
        # TODO: Log statistics
        
        self.rf_state = 'NONE'
        
        # Forward to network if enabled
        if self.network and self.network.is_connected():
            self.network.write(EOT_SYNC)

    def _handle_rf_timeout(self):
        """Handle RF timeout"""
        if self.rf_state != 'PROCESS':
            return
            
        logging.warning("M17 RF timeout")
        self.rf_state = 'NONE'
        
        # Forward EOT to network
        if self.network and self.network.is_connected():
            self.network.write(EOT_SYNC)

    def _handle_net_link_setup(self, data: bytes):
        """Handle network link setup frame"""
        if self.net_state != 'NONE':
            return
            
        # TODO: Extract and validate LSF fields
        
        self.net_state = 'PROCESS'
        self.net_timeout = time.time() + self.tx_hang
        self.net_frames = 0
        self.net_bits = 0
        self.net_errs = 0

    def _handle_net_stream(self, data: bytes):
        """Handle network stream frame"""
        if self.net_state != 'PROCESS':
            return
            
        # TODO: Extract and validate stream fields
        
        self.net_frames += 1
        self.net_timeout = time.time() + self.tx_hang

    def _handle_net_eot(self):
        """Handle network end of transmission"""
        if self.net_state != 'PROCESS':
            return
            
        # TODO: Log statistics
        
        self.net_state = 'NONE'

    def _handle_net_timeout(self):
        """Handle network timeout"""
        if self.net_state != 'PROCESS':
            return
            
        logging.warning("M17 network timeout")
        self.net_state = 'NONE'