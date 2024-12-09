# MMDVMHost

## Overview

MMDVMHost is a program that interfaces between MMDVM/DVMega hardware and various digital voice networks. It supports:

- On MMDVM: D-Star, DMR, P25 Phase 1, NXDN, System Fusion, M17, POCSAG, FM, and AX.25
- On DVMega: D-Star, DMR, and System Fusion

## Network Connectivity

The software interfaces with multiple network gateways:
- D-Star: Connects to the ircDDB Gateway
- DMR: Connects to the DMR Gateway for multiple network access, or directly to a single network
- System Fusion: Uses YSF Gateway for FCS and YSF network access
- P25: Interfaces with the P25 Gateway
- NXDN: Uses NXDN Gateway for NXDN and NXCore talk groups
- M17: Connects to M17 reflector system via M17 Gateway
- DAPNET: Accesses DAPNET for paging messages
- FM: Interfaces with existing FM networks via FM Gateway

## Build Support

The software builds on:
- 32-bit and 64-bit Linux
- Windows (using Visual Studio 2019) on x86 and x64

## Display Support

MMDVMHost can optionally control various displays:

```text
- HD44780 (sizes 2x16, 2x40, 4x16, 4x20)
        - Support for HD44780 via 4 bit GPIO connection (user selectable pins)
        - Adafruit 16x2 LCD+Keypad Kits (I2C)
        - Connection via PCF8574 GPIO Extender (I2C)
- Nextion TFTs (all sizes, both Basic and Enhanced versions)
- OLED 128x64 (SSD1306)
- LCDproc
```

### Display Connection Details

#### Nextion Displays
Nextion displays can be connected via:
- UART on the Raspberry Pi
- USB to TTL serial converter (e.g., FT-232RL)
- UART output of the MMDVM modem (Arduino Due, STM32, Teensy)

#### HD44780 Displays
HD44780 displays are integrated with wiringPi for Raspberry Pi based platforms.

#### OLED Displays
The OLED display requires an additional library. See [OLED.md](OLED.md) for details.

#### LCDproc
LCDproc support enables the use of many additional LCD screens. See the [supported devices](http://lcdproc.omnipotent.net/hardware.php3) page on the LCDproc website for more information.

## License

This software is licensed under the GPL v2 and is primarily intended for amateur and educational use.
