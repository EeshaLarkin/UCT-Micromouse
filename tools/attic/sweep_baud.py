import serial
import glob
import string
import time

import sys
import serial.tools.list_ports

def find_ports():
    found_ports = []
    for p in serial.tools.list_ports.comports():
        desc = p.description.lower() if p.description else ""
        if any(x in desc for x in ['stlink', 'st-link', 'stm32', 'virtual com', 'usbmodem', 'usbserial']):
            found_ports.append(p.device)
    if not found_ports:
        if sys.platform == 'darwin':
            found_ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/cu.usbserial*')
        elif sys.platform.startswith('linux'):
            found_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
        elif sys.platform == 'win32':
            # On Windows, list_ports is usually reliable, but return any port as guess
            ports = list(serial.tools.list_ports.comports())
            if ports: found_ports.append(ports[0].device)
    return found_ports

ports = find_ports()
if not ports:
    print("No ST-Link VCP found!")
    sys.exit(1)

port = ports[0]
# Standard baud rates + STM32 clock miscalculation variants (5x off)
bauds = [
    9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1843200,
    115200 * 5, 115200 // 5, 1843200 * 5, 1843200 // 5
]

printable = set(bytes(string.printable, 'ascii')) | {b'\r'[0], b'\n'[0]}

print(f"Sweeping baud rates on {port}...\n")

for baud in bauds:
    print(f"Testing {baud:7d} baud... ", end="", flush=True)
    try:
        with serial.Serial(port, baud, timeout=0.6) as ser:
            ser.read(ser.in_waiting) # Flush stale bytes
            data = ser.read(50)      # Wait for a chunk of data
            
            if not data:
                print("Silent.")
                continue
                
            score = sum(1 for b in data if b in printable) / len(data)
            print(f"Score: {score*100:3.0f}% readable ASCII")
            
            if score > 0.90:
                print(f"\nSUCCESS! The true baud rate is {baud}!")
                print(f"Decoded: {data.decode('ascii', errors='replace')}")
                break
    except Exception as e:
        print(f"Failed: {e}")