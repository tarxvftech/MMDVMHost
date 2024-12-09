# MMDVM Serial Protocol Specification

## Frame Format

Every frame follows this structure:

```
+------------+------------+------------+------------+------------+
| Start (1B) | Length MSB | Length LSB | Type (1B)  | Payload   |
+------------+------------+------------+------------+------------+
    0xE0        Length high  Length low   Command     Data...
```

- Start: Always 0xE0
- Length: 16-bit big-endian value, includes Type and Payload
- Type: Command type
- Payload: Command-specific data

## Command Types

### Get Version (0x00)
- Direction: Host → Modem
- Response: Version Info (0x00)
- Payload: None

Version Info Response:
```
+------------+------------+------------+------------+------------+
| Protocol   | Hardware   | Caps1      | Caps2      |
+------------+------------+------------+------------+------------+
  Version      HW Type     Capabilities Capabilities
```

### Get Status (0x01)
- Direction: Host → Modem
- Response: Status (0x01)
- Payload: None

Status Response:
```
+------------+
| Flags      |
+------------+
  bit 0: TX
  bit 1: CD (Carrier Detect)
  bit 2: Lockout
  bit 3: Error
```

### Set Config (0x02)
- Direction: Host → Modem
- Response: ACK/NAK
- Payload:
```
+------------+------------+------------+------------+------------+
| RX Freq    | TX Freq    | Power      | Flags      | ...       |
+------------+------------+------------+------------+------------+
  4 bytes      4 bytes     1 byte       1 byte       Mode config
```

### Set Mode (0x03)
- Direction: Host → Modem
- Response: ACK/NAK
- Payload:
```
+------------+
| Mode       |
+------------+
  0x00: IDLE
  0x01: D-STAR
  0x02: DMR
  0x03: YSF
  0x04: P25
  0x05: NXDN
  0x06: M17
  0x07: FM
  0x08: AX.25
```

### Frame Types

#### D-STAR Data (0x20)
```
+------------+------------+
| Header     | Data       |
+------------+------------+
  2 bytes      Data...
```

#### DMR Data (0x22/0x23)
```
+------------+------------+
| Slot Type  | Data       |
+------------+------------+
  1 byte       Data...

0x22: Slot 1
0x23: Slot 2
```

#### System Fusion Data (0x24)
```
+------------+------------+
| Length     | Data       |
+------------+------------+
  1 byte       Data...
```

#### P25 Data (0x25)
```
+------------+------------+
| NAC        | Data       |
+------------+------------+
  1 byte       Data...
```

#### NXDN Data (0x26)
```
+------------+------------+
| RAN        | Data       |
+------------+------------+
  1 byte       Data...
```

#### M17 Data (0x27)
```
+------------+------------+
| CAN        | Data       |
+------------+------------+
  2 bytes      Data...
```

#### FM Data (0x28)
```
+------------+------------+
| Type       | Data       |
+------------+------------+
  1 byte       Audio...
```

#### AX.25 Data (0x29)
```
+------------+------------+
| Flags      | Data       |
+------------+------------+
  1 byte       Frame...
```

### Control Commands

#### Set RF Params (0x02)
```
+------------+------------+------------+------------+
| RX Freq    | TX Freq    | Power      | Flags     |
+------------+------------+------------+------------+
  4 bytes      4 bytes     1 byte       1 byte
```

#### Set Modem Config (0x04)
```
+------------+------------+------------+------------+
| TX Delay   | RX Level   | TX Level   | RF Level  |
+------------+------------+------------+------------+
  1 byte       1 byte      1 byte       1 byte
```

#### Send CW ID (0x0E)
```
+------------+
| Callsign   |
+------------+
  ASCII text
```

## Error Handling

### NAK Response (0xFF)
Sent by modem when command fails:
```
+------------+------------+
| Error Code | Command    |
+------------+------------+
  1 byte       Failed cmd
```

Error codes:
- 0x01: Invalid command
- 0x02: Wrong mode
- 0x03: Invalid data
- 0x04: Busy
- 0x05: Failed
- 0x06: Not supported

### Timeouts
- Command timeout: 100ms
- Data timeout: 20ms
- Keep-alive: Send Get Status every 1s

## Flow Control

- Host must wait for ACK/NAK before sending next command
- Data frames can be sent without waiting
- Modem will send NAK if buffer full
- Host should retry after NAK with backoff

## Initialization Sequence

1. Send Get Version
2. Wait for Version Info
3. Send Set Config
4. Wait for ACK
5. Send Set Mode (IDLE)
6. Wait for ACK
7. Begin normal operation