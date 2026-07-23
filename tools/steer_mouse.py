import curses
import time
import traceback
import sys
import os
import serial
import json

# Add the 'python' directory to the path so we can import micromouse.py
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from micromouse import Micromouse

def send_raw_command(ser, cmd):
    # Clear read buffer
    ser.read(ser.in_waiting)
    
    # Write command terminated by Ctrl-D (\x04)
    ser.write(cmd.encode('utf-8') + b'\x04')
    
    # Read response
    data = b''
    start_time = time.time()
    while time.time() - start_time < 0.8:
        if ser.in_waiting > 0:
            data += ser.read(ser.in_waiting)
            if data.endswith(b'\x04>'):
                break
        time.sleep(0.001)
        
    if not data.startswith(b'OK'):
        return "", f"No OK prefix: {data!r}"
        
    content = data[2:]  # Remove 'OK'
    if content.endswith(b'>'):
        content = content[:-1]
        
    parts = content.split(b'\x04')
    stdout = ""
    stderr = ""
    if len(parts) >= 1:
        stdout = parts[0].decode('utf-8', errors='ignore').strip()
    if len(parts) >= 2:
        stderr = parts[1].decode('utf-8', errors='ignore').strip()
        
    return stdout, stderr

def main(stdscr, method='tcp'):
    curses.curs_set(0)
    stdscr.nodelay(True)
    
    stdscr.clear()
    stdscr.addstr(0, 0, "=== UCT Micromouse Co-Simulation Dashboard ===")
    stdscr.addstr(1, 0, f"Connecting via {method.upper()}...")
    stdscr.refresh()

    mouse = None
    ser = None
    pwm_l, pwm_r = 0, 0
    s = {"tof_l": 0, "tof_c": 0, "tof_r": 0, "v_batt": 0.0}

    try:
        if method in ['tcp', 'serial']:
            mouse = Micromouse(method=method, verbose=False)
            mouse.connect()
            
            stdscr.addstr(1, 0, "Hardware connected! Syncing telemetry...       ")
            stdscr.refresh()
            mouse.configure(data='d', sync=1)
        else:
            # MicroPython REPL mode
            port = args.port if args.port else Micromouse().find_serial_port()
            if not port:
                raise ConnectionError("No MicroPython serial port found! Is the board plugged in?")
            
            stdscr.addstr(1, 0, f"Connecting to REPL on {port}...       ")
            stdscr.refresh()
            ser = serial.Serial(port, 115200, timeout=0.1)
            
            # Exit Raw REPL first (in case we were stuck in it), then interrupt any running script
            ser.write(b"\x02\r\n\x03\x03\r\n")
            
            # Wait for standard REPL prompt '>>> ' to ensure script has fully stopped and traceback printed
            data = b""
            start_time = time.time()
            while time.time() - start_time < 3.0:
                if ser.in_waiting > 0:
                    data += ser.read(ser.in_waiting)
                    if data.endswith(b'>>> '):
                        break
                time.sleep(0.01)
            
            # Enter Raw REPL mode
            ser.write(b"\x01")
            
            # Wait for raw REPL prompt '>' to ensure the buffer is fully sync'd
            data = b""
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if ser.in_waiting > 0:
                    data += ser.read(ser.in_waiting)
                    if data.endswith(b'>'):
                        break
                time.sleep(0.01)
            
            # Initialize uct_mouse via Raw REPL
            stdout, stderr = send_raw_command(ser, "import uct_mouse; uct_mouse.init()")
            if stderr:
                raise RuntimeError(f"Initialization failed: {stderr}")

        while True:
            key = stdscr.getch()
            
            actuate = False
            if key == ord('q'):
                break
            elif key == ord(' '):
                pwm_l, pwm_r = 0, 0
                actuate = True
            elif key == curses.KEY_UP:
                pwm_l, pwm_r = 100, 100
                actuate = True
            elif key == curses.KEY_DOWN:
                pwm_l, pwm_r = -100, -100
                actuate = True
            elif key == curses.KEY_LEFT:
                pwm_l, pwm_r = -60, 60
                actuate = True
            elif key == curses.KEY_RIGHT:
                pwm_l, pwm_r = 60, -60
                actuate = True
            
            if method in ['tcp', 'serial']:
                if actuate:
                    mouse.set_pwm(pwm_l, pwm_r)
                else:
                    mouse.poll()
                
                s = mouse.get_sensors()
                raw_tx = mouse.last_tx
                raw_rx = mouse.last_rx
            else:
                # REPL mode
                if actuate:
                    cmd = f"uct_mouse.set_motors({pwm_l}, {pwm_r})"
                    stdout, stderr = send_raw_command(ser, cmd)
                    raw_tx = cmd
                    raw_rx = stdout if not stderr else f"ERR: {stderr}"
                else:
                    cmd = "print('T:', uct_mouse.get_tof(), 'B:', uct_mouse.get_vbatt())"
                    stdout, stderr = send_raw_command(ser, cmd)
                    raw_tx = cmd
                    raw_rx = stdout if not stderr else f"ERR: {stderr}"
                    
                    if not stderr and "T:" in stdout and "B:" in stdout:
                        try:
                            parts = stdout.split("B:")
                            v_batt = float(parts[1].strip())
                            tof_part = parts[0].split("T:")[1].strip()
                            tof_vals = eval(tof_part)
                            s["tof_l"], s["tof_c"], s["tof_r"] = tof_vals[0], tof_vals[2], tof_vals[4]
                            s["v_batt"] = v_batt
                        except Exception:
                            pass
            
            stdscr.clear()
            stdscr.addstr(0, 0, "=== UCT Micromouse Keyboard steering Dashboard ===")
            stdscr.addstr(1, 0, "Connected! Steer with ARROWS. SPACE to brake. 'q' to quit.")
            stdscr.addstr(3, 0, f"Motor Intent : Left={pwm_l:<4} | Right={pwm_r:<4}")
            stdscr.addstr(4, 0, f"ToF Sensors  : L={s.get('tof_l',0):<4} | C={s.get('tof_c',0):<4} | R={s.get('tof_r',0):<4}")
            stdscr.addstr(5, 0, f"Battery      : {s.get('v_batt', 0.0):.2f} V")
            
            stdscr.addstr(7, 0, "-" * 60)
            stdscr.addstr(8, 0, f"RAW TX: {raw_tx:<52}"[:60])
            stdscr.addstr(9, 0, f"RAW RX: {raw_rx:<52}"[:60])
            stdscr.addstr(10, 0, "-" * 60)
            
            stdscr.refresh()
            time.sleep(0.05)
            
    except ConnectionError as e:
        stdscr.nodelay(False)
        stdscr.clear()
        stdscr.addstr(0, 0, "=== CONNECTION CLOSED ===")
        stdscr.addstr(2, 0, "The connection to the simulation server was closed.")
        stdscr.addstr(4, 0, "This usually occurs when:")
        stdscr.addstr(5, 4, "1. The mouse crashed into a wall (Collision detected).")
        stdscr.addstr(6, 4, "2. The simulation reached its time limit.")
        stdscr.addstr(7, 4, "3. The MATLAB simulation was stopped manually.")
        stdscr.addstr(9, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        
    except Exception as e:
        stdscr.nodelay(False)
        stdscr.clear()
        stdscr.addstr(0, 0, "=== FATAL ERROR ENCOUNTERED ===")
        stdscr.addstr(2, 0, str(e))
        
        tb = traceback.format_exc().splitlines()
        for i, line in enumerate(tb[-15:]):
            if 4 + i < curses.LINES - 2:
                stdscr.addstr(4 + i, 0, line)
                
        stdscr.addstr(curses.LINES - 1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        
    finally:
        if method in ['tcp', 'serial']:
            if mouse and mouse.connected:
                try:
                    mouse.set_pwm(0, 0)
                except Exception:
                    pass
        else:
            if ser and ser.is_open:
                try:
                    send_raw_command(ser, "uct_mouse.set_motors(0, 0)")
                    # Exit Raw REPL mode by sending Ctrl-B (\x02) to restore normal REPL
                    ser.write(b"\x02")
                    time.sleep(0.1)
                except Exception:
                    pass
                finally:
                    try:
                        ser.close()
                    except Exception:
                        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Steer Micromouse via keyboard")
    parser.add_argument(
        "--method", "-m",
        choices=["tcp", "serial", "repl"],
        default="tcp",
        help="Connection method: 'tcp' for Simulink simulation, 'serial' for PikaScript/Simulink hardware tether, 'repl' for MicroPython hardware REPL (default: tcp)"
    )
    parser.add_argument(
        "--port", "-p",
        default=None,
        help="Manually specify serial VCP port (e.g. /dev/cu.usbmodem3054337831352)"
    )
    args = parser.parse_args()
    curses.wrapper(lambda stdscr: main(stdscr, args.method))