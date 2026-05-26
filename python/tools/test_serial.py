import serial
import glob
import time
import sys

def test_serial():
    ports = glob.glob('/dev/cu.usbmodem*')
    if not ports:
        print("No ST-Link VCP found! Is the board plugged in?")
        sys.exit(1)
        
    port = ports[0]
    print(f"Connecting to {port} at 115200 baud...")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
        
        # Assert DTR/RTS to hard-reset the STM32
        ser.dtr = True
        ser.rts = True
        time.sleep(0.1)
        ser.dtr = False
        ser.rts = False
        
        print("Board reset. Listening for raw bytes for 5 seconds...\n")
        print("-" * 50)
        
        end_time = time.time() + 5.0
        while time.time() < end_time:
            if ser.in_waiting > 0:
                raw_data = ser.read(ser.in_waiting)
                print(f"RAW: {raw_data}")
            time.sleep(0.01)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_serial()