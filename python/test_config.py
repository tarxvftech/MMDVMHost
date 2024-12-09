#!/usr/bin/env python3
"""
Test script for MMDVMHost configuration
"""

from mmdvm_host import MMDVMHost

def main():
    """Main test function"""
    host = MMDVMHost("MMDVM.ini")
    
    print(f"Callsign: {host.config.get('General', 'Callsign')}")
    print(f"ID: {host.config.getint('General', 'Id')}")
    print(f"Timeout: {host.config.getint('General', 'Timeout')}")
    print(f"Duplex: {host.config.getboolean('General', 'Duplex')}")
    print()
    
    print("Mode Enables:")
    print(f"D-Star: {host.config.getboolean('D-Star', 'Enable')}")
    print(f"DMR: {host.config.getboolean('DMR', 'Enable')}")
    print(f"System Fusion: {host.config.getboolean('System Fusion', 'Enable')}")
    print(f"P25: {host.config.getboolean('P25', 'Enable')}")
    print(f"NXDN: {host.config.getboolean('NXDN', 'Enable')}")
    print(f"M17: {host.config.getboolean('M17', 'Enable')}")
    print(f"POCSAG: {host.config.getboolean('POCSAG', 'Enable')}")
    print(f"FM: {host.config.getboolean('FM', 'Enable')}")
    print(f"AX.25: {host.config.getboolean('AX.25', 'Enable')}")
    print()
    
    print("Mode Hangs:")
    print(f"D-Star: {host.config.getint('D-Star', 'ModeHang', fallback=10)}")
    print(f"DMR: {host.config.getint('DMR', 'ModeHang', fallback=10)}")
    print(f"System Fusion: {host.config.getint('System Fusion', 'ModeHang', fallback=10)}")
    print(f"P25: {host.config.getint('P25', 'ModeHang', fallback=10)}")
    print(f"NXDN: {host.config.getint('NXDN', 'ModeHang', fallback=10)}")
    print(f"M17: {host.config.getint('M17', 'ModeHang', fallback=10)}")
    print(f"FM: {host.config.getint('FM', 'ModeHang', fallback=10)}")
    print()
    
    print("Network Enables:")
    print(f"D-Star: {host.config.getboolean('D-Star Network', 'Enable')}")
    print(f"DMR: {host.config.getboolean('DMR Network', 'Enable')}")
    print(f"System Fusion: {host.config.getboolean('System Fusion Network', 'Enable')}")
    print(f"P25: {host.config.getboolean('P25 Network', 'Enable')}")
    print(f"NXDN: {host.config.getboolean('NXDN Network', 'Enable')}")
    print(f"M17: {host.config.getboolean('M17 Network', 'Enable')}")
    print(f"POCSAG: {host.config.getboolean('POCSAG Network', 'Enable')}")
    print(f"FM: {host.config.getboolean('FM Network', 'Enable')}")
    print(f"AX.25: {host.config.getboolean('AX.25 Network', 'Enable')}")

if __name__ == "__main__":
    main()