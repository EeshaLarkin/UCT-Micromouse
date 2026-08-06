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

def attempt_dump(port, baudrate):
    print(f"Connecting to {port} at {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=1.0)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return None

    # Clear input buffer of any active telemetry streams
    ser.reset_input_buffer()
    
    # Exiting raw REPL if MicroPython is locked up
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
    timeout = 8.0 # 8s max read timeout for this attempt

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
        except Exception as e:
            print(f"Error reading stream: {e}")
            break

    ser.close()
    
    if started and finished:
        return lines
    return None

def main():
    parser = argparse.ArgumentParser(description="UCT Micromouse Serial Log Extractor")
    parser.add_argument("-p", "--port", help="Serial port of the mouse (auto-detected if omitted)")
    parser.add_argument("-o", "--output", default="run_log.jsonl", help="Output file path (default: run_log.jsonl)")
    args = parser.parse_args()

    port = args.port or detect_port()
    if not port:
        sys.exit(1)

    # Try standard 115200 baud first
    lines = attempt_dump(port, 115200)
    
    # If 115200 fails, try the 72 MHz silicon outlier fallback at 103680 baud
    if lines is None:
        print("[Baud Sweep] 115200 baud timed out. Attempting 72 MHz silicon outlier fallback at 103680 baud...")
        lines = attempt_dump(port, 103680)

    if lines is None:
        print("Error: Log dump failed. Make sure the mouse is powered on, flashed with the C-Kernel, and the correct port is selected.")
        sys.exit(1)

    # Write captured telemetry lines to output file
    with open(args.output, "w") as f:
        for l in lines:
            f.write(l + "\n")
    print(f"Saved {len(lines)} log records to: {args.output}")

if __name__ == "__main__":
    main()
