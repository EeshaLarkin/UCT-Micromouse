import serial
import glob
import time
import sys
import serial.tools.list_ports

def find_ports():
    # 1. Search dynamically using serial.tools.list_ports.comports()
    found_ports = []
    for p in serial.tools.list_ports.comports():
        desc = p.description.lower()
        hwid = p.hwid.lower()
        dev = p.device.lower()
        # Look for typical STM32 / ST-Link / USB-to-Serial signatures
        if any(x in desc or x in hwid or x in dev for x in ['stlink', 'st-link', 'stm32', 'virtual com', 'usbmodem', 'usbserial']):
            found_ports.append(p.device)
            
    # 2. Fallback to glob patterns if list_ports didn't catch it
    if not found_ports:
        if sys.platform == 'darwin':
            found_ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/cu.usbserial*')
        elif sys.platform.startswith('linux'):
            found_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
            
    return found_ports

def test_serial():
    ports = find_ports()
    if not ports:
        print("No ST-Link VCP found! Is the board plugged in?")
        print("Available serial ports on your system:")
        for p in serial.tools.list_ports.comports():
            print(f"  -> {p.device} ({p.description})")
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