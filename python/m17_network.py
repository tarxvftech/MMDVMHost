#!/usr/bin/env python3
"""
M17 network handler
"""

import logging
import random
import socket
import threading
import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Optional, Tuple

from m17_defines import *


@dataclass
class M17Network:
    """M17 network handler"""
    local_address: str
    local_port: int
    gateway_address: str
    gateway_port: int
    debug: bool = False
    
    # Internal state
    socket: Optional[socket.socket] = None
    enabled: bool = False
    out_id: int = field(default_factory=lambda: random.randint(0, 65535))
    in_id: int = 0
    buffer: Queue = field(default_factory=lambda: Queue(maxsize=3000))
    last_ping: float = 0
    connected: bool = False
    running: bool = False
    rx_thread: Optional[threading.Thread] = None

    def open(self) -> bool:
        """Open network connection"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.local_address, self.local_port))
            self.socket.settimeout(1)
            
            # Start receive thread
            self.running = True
            self.rx_thread = threading.Thread(target=self._rx_loop)
            self.rx_thread.daemon = True
            self.rx_thread.start()
            
            # Send initial ping
            self.send_ping()
            
            return True
            
        except Exception as e:
            logging.error(f"Error opening M17 network: {e}")
            return False

    def enable(self, enabled: bool):
        """Enable/disable network"""
        self.enabled = enabled
        if not enabled:
            self.connected = False

    def write(self, data: bytes) -> bool:
        """Write data to network"""
        if not self.enabled or not self.socket:
            return False
            
        try:
            addr = (self.gateway_address, self.gateway_port)
            sent = self.socket.sendto(data, addr)
            return sent == len(data)
        except Exception as e:
            logging.error(f"Error writing to M17 network: {e}")
            return False

    def read(self) -> Optional[bytes]:
        """Read data from network"""
        if not self.enabled:
            return None
            
        try:
            return self.buffer.get_nowait()
        except:
            return None

    def reset(self):
        """Reset network state"""
        self.out_id = random.randint(0, 65535)
        self.in_id = 0
        self.connected = False
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except:
                pass

    def close(self):
        """Close network connection"""
        self.running = False
        if self.rx_thread:
            self.rx_thread.join()
        if self.socket:
            self.socket.close()
            self.socket = None

    def clock(self, ms: int):
        """Clock tick handler"""
        if not self.enabled:
            return
            
        # Send ping every 5 seconds
        now = time.time()
        if now - self.last_ping >= 5.0:
            self.send_ping()
            self.last_ping = now

    def is_connected(self) -> bool:
        """Check if connected to gateway"""
        return self.connected

    def _rx_loop(self):
        """Background receive thread"""
        while self.running and self.socket:
            try:
                data, addr = self.socket.recvfrom(2048)
                if data:
                    if addr[0] == self.gateway_address and addr[1] == self.gateway_port:
                        # Process received data
                        if len(data) > 0:
                            if data[0] == 0x00:  # Ping response
                                self.connected = True
                            else:
                                try:
                                    self.buffer.put_nowait(data)
                                except:
                                    pass
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    logging.error(f"Error receiving from M17 network: {e}")

    def send_ping(self):
        """Send ping to gateway"""
        if not self.socket:
            return
            
        try:
            ping = bytes([0x00, self.out_id >> 8, self.out_id & 0xFF])
            addr = (self.gateway_address, self.gateway_port)
            self.socket.sendto(ping, addr)
        except Exception as e:
            logging.error(f"Error sending M17 ping: {e}")
            self.connected = False