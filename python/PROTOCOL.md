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

## Example Sequences

### Initialization
```python
# Get version info
modem.write(bytes([0xE0, 0x00, 0x01, 0x00]))
version = modem.read()  # Expect: [0xE0, 0x00, 0x05, 0x00, ver, hw, caps1, caps2]

# Set configuration
modem.write(bytes([
    0xE0, 0x00, 0x18, 0x02,  # Header
    0x01, 0x02, 0x03, 0x04,  # RX Freq (435.0 MHz)
    0x01, 0x02, 0x03, 0x04,  # TX Freq
    0x32,                     # Power (50%)
    0x00                      # Flags
]))
modem.read()  # Expect ACK

# Set IDLE mode
modem.write(bytes([0xE0, 0x00, 0x02, 0x03, 0x00]))
modem.read()  # Expect ACK
```

### D-STAR Mode
```python
# Enable D-STAR mode
modem.write(bytes([0xE0, 0x00, 0x02, 0x03, 0x01]))
modem.read()  # Expect ACK

# Send D-STAR data
data = b'...'  # Your D-STAR frame
modem.write(bytes([0xE0, len(data) + 1, 0x20]) + data)
```

### DMR Mode
```python
# Enable DMR mode
modem.write(bytes([0xE0, 0x00, 0x02, 0x03, 0x02]))
modem.read()  # Expect ACK

# Send DMR data on Slot 1
data = b'...'  # Your DMR frame
modem.write(bytes([0xE0, len(data) + 1, 0x22]) + data)

# Send DMR data on Slot 2
modem.write(bytes([0xE0, len(data) + 1, 0x23]) + data)
```

### System Fusion Mode
```python
# Enable YSF mode
modem.write(bytes([0xE0, 0x00, 0x02, 0x03, 0x03]))
modem.read()  # Expect ACK

# Send YSF data
data = b'...'  # Your YSF frame
modem.write(bytes([0xE0, len(data) + 1, 0x24]) + data)
```

### M17 Mode
```python
# Enable M17 mode
modem.write(bytes([0xE0, 0x00, 0x02, 0x03, 0x06]))
modem.read()  # Expect ACK

# Send M17 LSF
lsf = b'...'  # Your LSF data
modem.write(bytes([0xE0, len(lsf) + 1, 0x27]) + lsf)

# Send M17 stream frame
frame = b'...'  # Your stream frame
modem.write(bytes([0xE0, len(frame) + 1, 0x27]) + frame)
```

## Receiving Data

Data from the modem comes in the same frame format as sending. The process is:

1. Read start byte (0xE0)
2. Read length (2 bytes)
3. Read type
4. Read payload (length - 1 bytes)

Example implementation:
```python
def read_frame():
    # Wait for start byte
    while True:
        b = modem.read(1)
        if b == b'\xE0':
            break
            
    # Read length
    length_bytes = modem.read(2)
    length = int.from_bytes(length_bytes, 'big')
    
    # Read type and payload
    data = modem.read(length)
    if not data:
        return None
        
    frame_type = data[0]
    payload = data[1:]
    
    return frame_type, payload

def process_frames():
    while True:
        frame = read_frame()
        if not frame:
            continue
            
        frame_type, payload = frame
        
        if frame_type == 0x00:  # Version info
            protocol, hw_type, caps1, caps2 = payload
            print(f"Version: {protocol}.{hw_type}")
            
        elif frame_type == 0x01:  # Status
            flags = payload[0]
            tx_active = bool(flags & 0x01)
            rx_active = bool(flags & 0x02)
            
        elif frame_type == 0x20:  # D-STAR data
            process_dstar(payload)
            
        elif frame_type in (0x22, 0x23):  # DMR data
            slot = 1 if frame_type == 0x22 else 2
            process_dmr(slot, payload)
            
        elif frame_type == 0x27:  # M17 data
            process_m17(payload)
```

The modem will send data frames whenever it receives RF data in the current mode. You should:

1. Run the receive process in a separate thread
2. Use a queue to handle received frames
3. Process frames according to the current mode
4. Watch for status updates and errors
5. Handle timeouts appropriately

Example frame handler:
```python
def handle_frames(modem, queue):
    while True:
        try:
            frame_type, payload = read_frame()
            queue.put((frame_type, payload))
        except TimeoutError:
            continue
        except Exception as e:
            print(f"Error reading frame: {e}")
            break

# In main code
rx_queue = Queue()
rx_thread = Thread(target=handle_frames, args=(modem, rx_queue))
rx_thread.daemon = True
rx_thread.start()

# Process received frames
while True:
    try:
        frame_type, payload = rx_queue.get(timeout=1.0)
        process_frame(frame_type, payload)
    except Empty:
        # Send status request to keep alive
        modem.write(bytes([0xE0, 0x00, 0x01, 0x01]))
```

## Important Implementation Details

### Buffer Management
- The modem has limited buffer space
- Each mode has separate RX and TX buffers
- Buffer sizes:
  - D-STAR: 4800 bytes
  - DMR: 2 x 2400 bytes (one per slot)
  - YSF: 2400 bytes
  - P25: 2400 bytes
  - NXDN: 2400 bytes
  - M17: 2400 bytes
  - FM: 4800 bytes
  - AX.25: 2400 bytes

You must:
1. Check space available before sending (`hasXXXSpace()` commands)
2. Handle NAK responses when buffers full
3. Implement backoff when buffers fill
4. Clear buffers when changing modes

### Timing Requirements
- Maximum frame processing time: 10ms
- Minimum inter-frame gap: 2ms
- Mode switch settling time: 100ms
- Keep-alive interval: 1000ms
- Command timeout: 100ms
- Response timeout: 50ms
- Retry interval: 25ms (with exponential backoff)

### Mode Switching
When switching modes:
1. Stop all data transmission
2. Wait for buffers to empty
3. Send mode change command
4. Wait for ACK
5. Wait settling time
6. Clear all buffers
7. Reset state machines
8. Start new mode

### Error Recovery
Common errors and recovery:
1. Lost sync:
   - Stop sending
   - Send Get Status
   - Wait for response or timeout
   - If timeout, reset modem
   - Re-initialize from scratch

2. Buffer overflow:
   - Stop sending
   - Wait 100ms
   - Request status
   - Resume with backoff

3. Mode hang:
   - Send mode IDLE
   - Wait 100ms
   - Try mode switch again
   - If fails, reset modem

4. Corrupted frame:
   - Discard partial frame
   - Look for next 0xE0
   - Resync frame boundary
   - Request retransmission if needed

### Thread Safety
Critical sections that need locking:
1. Mode changes
2. Buffer access
3. Status updates
4. Configuration changes
5. Serial port access

Example lock usage:
```python
class ModemManager:
    def __init__(self):
        self._mode_lock = Lock()
        self._buffer_lock = Lock()
        self._status_lock = Lock()
        self._port_lock = Lock()

    def change_mode(self, new_mode):
        with self._mode_lock:
            # Stop current mode
            with self._buffer_lock:
                self._flush_buffers()
            
            # Switch modes
            with self._port_lock:
                self._send_mode_cmd(new_mode)
                self._wait_ack()
            
            # Initialize new mode
            time.sleep(0.1)  # Settling time
```

### Debugging Tips
1. Frame logging:
```python
def log_frame(direction: str, frame: bytes):
    print(f"{direction}: {frame.hex()}")
    if frame[0] != 0xE0:
        print("Warning: Invalid start byte")
    if len(frame) < 4:
        print("Warning: Frame too short")
    if direction == "RX" and frame[3] == 0xFF:
        print("Warning: NAK received")
```

2. Status monitoring:
```python
def monitor_status():
    while True:
        status = get_status()
        print(f"TX: {status.tx_active}")
        print(f"RX: {status.rx_active}")
        print(f"Buffer: {status.buffer_space}")
        time.sleep(1)
```

3. Performance tracking:
```python
def track_timing():
    times = []
    for _ in range(100):
        start = time.monotonic()
        read_frame()
        times.append(time.monotonic() - start)
    print(f"Avg: {sum(times)/len(times)*1000:.1f}ms")
    print(f"Max: {max(times)*1000:.1f}ms")
```

### Common Pitfalls
1. Not handling partial reads from serial port
2. Not checking buffer space before sending
3. Missing mode settling time
4. Race conditions in thread handling
5. Not implementing proper backoff
6. Forgetting keep-alive messages
7. Buffer overflow in receive queue
8. Not handling all error cases
9. Missing frame boundary resync
10. Incorrect length calculations

### Testing
Recommended test sequence:
1. Basic connectivity
   ```python
   # Test modem presence
   write_frame(GET_VERSION)
   assert read_frame().type == VERSION_INFO
   ```

2. Mode switching
   ```python
   # Test all mode transitions
   for mode in MODES:
       switch_mode(mode)
       assert get_status().mode == mode
       switch_mode(IDLE)
       assert get_status().mode == IDLE
   ```

3. Buffer handling
   ```python
   # Fill buffer and verify NAK
   while True:
       if not write_frame(TEST_DATA):
           break
   assert read_frame().type == NAK
   ```

4. Error injection
   ```python
   # Test recovery from errors
   send_invalid_frame()
   assert modem.recover()
   ```

5. Performance testing
   ```python
   # Measure throughput
   start = time.monotonic()
   bytes_sent = send_test_pattern()
   duration = time.monotonic() - start
   print(f"Rate: {bytes_sent/duration/1024:.1f} KiB/s")
   ```