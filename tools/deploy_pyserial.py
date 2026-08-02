import serial
import time
import sys
import os

def deploy():
    import glob
    ports = glob.glob('/dev/cu.usbmodem*')
    target_ports = [p for p in ports if len(os.path.basename(p)) >= 20]
    if not target_ports:
        target_ports = [p for p in ports if '11302' not in p]
    if not target_ports:
        print("No usbmodem port found!")
        sys.exit(1)
    port = target_ports[0]
    print(f"Connecting to dynamically detected port: {port}...")
    s = serial.Serial(port, 115200, timeout=1)
    
    # 1. Break loop and wait for >>> prompt
    print("Interrupting board...")
    for i in range(10):
        s.write(b'\x03')
        time.sleep(0.2)
        resp = s.read_all()
        if b'>>>' in resp:
            print("Found REPL prompt.")
            break
    else:
        # Check if already in raw REPL
        s.write(b'\x02') # Ctrl-B to exit raw REPL
        time.sleep(0.5)
        resp = s.read_all()
        if b'>>>' in resp:
            print("Exited raw REPL back to normal REPL.")
        else:
            print(f"Could not interrupt board. Response: {resp}")
    
    # 2. Enter raw REPL
    print("Entering raw REPL...")
    for i in range(5):
        s.write(b'\x01') # Ctrl-A to enter raw REPL
        time.sleep(0.5)
        resp = s.read_all()
        if b'raw REPL' in resp:
            print("Entered raw REPL successfully.")
            break
    else:
        print(f"Failed to enter raw REPL. Last response: {resp}")
        sys.exit(1)
        
    def run_cmd(cmd):
        s.write(cmd.encode('utf-8') + b'\x04')
        time.sleep(0.5)
        res = s.read_all()
        return res

    # 3. Write boot.py
    print("Writing boot.py...")
    with open('python/boot.py', 'r') as f:
        boot_code = f.read()
    run_cmd(f"f = open('boot.py', 'w')\nf.write({repr(boot_code)})\nf.close()\n")

    # 4. Write main.py
    print("Writing main.py...")
    with open('workspace/main.py', 'r') as f:
        main_code = f.read()
    run_cmd(f"f = open('main.py', 'w')\nf.write({repr(main_code)})\nf.close()\n")

    # 5. Exit raw REPL and soft reboot
    print("Exiting raw REPL and soft-rebooting...")
    s.write(b'\x02') # Exit raw REPL
    time.sleep(0.1)
    s.write(b'\x04') # Soft reboot
    time.sleep(0.2)
    print("Successfully deployed workspace!")
    s.close()

if __name__ == '__main__':
    deploy()
