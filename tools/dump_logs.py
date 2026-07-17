#!/usr/bin/env python3
import sys
import time
import argparse
import serial
import serial.tools.list_ports

def detect_port():
    mpy_port = None
    stlink_port = None
    
    for p in serial.tools.list_ports.comports():
        # Check for ST-Link virtual COM port
        if "ST-Link" in p.description or "STLink" in p.description or (p.vid == 0x0483 and p.pid in (0x374b, 0x3752)) or "usbmodem" in p.device:
            stlink_port = p.device
        # Check for MicroPython VCP OTG port as fallback
        elif p.vid == 0xf055 and p.pid == 0x9800:
            mpy_port = p.device

    if stlink_port:
        print(f"[Port Detector] Found ST-Link Debug VCP port: {stlink_port}")
        return stlink_port
    elif mpy_port:
        print(f"[Port Detector] Found MicroPython OTG port (fallback): {mpy_port}")
        return mpy_port
    
    print("[Port Detector] Error: No compatible serial device detected!")
    return None

def main():
    parser = argparse.ArgumentParser(description="UCT Micromouse Serial Log Extractor")
    parser.add_argument("-p", "--port", help="Serial port of the mouse (auto-detected if omitted)")
    parser.add_argument("-o", "--output", default="run_log.jsonl", help="Output file path (default: run_log.jsonl)")
    args = parser.parse_args()

    port = args.port or detect_port()
    if not port:
        sys.exit(1)

    print(f"Connecting to {port}...")
    try:
        ser = serial.Serial(port, 115200, timeout=2.0)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    # Clear input buffer of any active telemetry streams
    ser.reset_input_buffer()
    
    # Exiting raw REPL if MicroPython is locked up
    print("Exiting raw REPL if locked...")
    ser.write(b'\x02') 
    time.sleep(0.2)
    ser.reset_input_buffer()

    print("Requesting log dump from C-Kernel...")
    # Send both command formats (one for MicroPython REPL, one for C-Kernel JSON)
    ser.write(b'\r\nimport uct_mouse; uct_mouse.dump_logs()\r\n')
    time.sleep(0.1)
    ser.write(b'\r\n{"c":{"dump":1}}\r\n')
    
    lines = []
    started = False
    finished = False
    start_time = time.time()
    timeout = 10.0 # 10s max read timeout

    while time.time() - start_time < timeout:
        try:
            line_bytes = ser.readline()
            if not line_bytes:
                continue
            line = line_bytes.decode('utf-8', errors='ignore').strip()
            
            if "--- START LOG DUMP ---" in line:
                print("Dump started...")
                started = True
                continue
            elif "--- END LOG DUMP ---" in line:
                print("Dump finished successfully.")
                finished = True
                break
            
            if started:
                # Filter out raw trailing padding spaces or empty lines
                line_clean = line.strip()
                if line_clean:
                    lines.append(line_clean)
        except KeyboardInterrupt:
            print("Capture interrupted by user.")
            break
        except Exception as e:
            print(f"Error reading stream: {e}")
            break

    ser.close()

    if not started:
        print("Error: Log dump never started. Make sure the mouse is powered on and flashed with the C-Kernel.")
        sys.exit(1)
        
    if not finished:
        print("Warning: Log dump capture timed out before seeing end marker.")

    # Write captured telemetry lines to output file
    if lines:
        with open(args.output, "w") as f:
            for l in lines:
                f.write(l + "\n")
        print(f"Saved {len(lines)} log records to: {args.output}")
    else:
        print("No log records captured.")

if __name__ == "__main__":
    main()
