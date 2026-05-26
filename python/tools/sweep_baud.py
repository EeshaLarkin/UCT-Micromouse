import serial
import glob
import string
import time

ports = glob.glob('/dev/cu.usbmodem*')
if not ports:
    print("No ST-Link VCP found!")
    exit(1)

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