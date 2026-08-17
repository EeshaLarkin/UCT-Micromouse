import sys
import serial
import threading
import time

PORT = '/dev/cu.UCTMouse'
BAUD = 115200

def read_from_port(ser):
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
            time.sleep(0.01)
        except Exception as e:
            print(f"\n[Error reading]: {e}")
            break

def main():
    print(f"Connecting to {PORT} at {BAUD} baud...")
    try:
        # Open with exact parameters that worked in test_bt.py
        ser = serial.Serial(PORT, BAUD, rtscts=False, dsrdtr=False, timeout=1.0)
        ser.dtr = True
        ser.rts = True
        
        # Flush buffers and send a quick wake-up byte
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        ser.write(b"\r\n")
        
        print("Connected successfully! Press Ctrl+C to exit.")
        print("-" * 50)
        
        # Start read thread
        t = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        t.start()
        
        # Write loop
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            ser.write(line.encode('utf-8'))
            
    except KeyboardInterrupt:
        print("\nExiting terminal.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            ser.close()
        except:
            pass

if __name__ == '__main__':
    main()
