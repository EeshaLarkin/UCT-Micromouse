import curses
import time
import traceback
from micromouse import Micromouse

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    
    stdscr.clear()
    stdscr.addstr(0, 0, "=== UCT Micromouse Co-Simulation Dashboard ===")
    stdscr.addstr(1, 0, "Connecting to Hardware...")
    stdscr.refresh()

    mouse = None
    pwm_l, pwm_r = 0, 0

    try:
        mouse = Micromouse(method='serial', verbose=False)
        mouse.connect()
        
        stdscr.addstr(1, 0, "Hardware connected! Syncing telemetry...       ")
        stdscr.refresh()
        mouse.configure(data='d', sync=1)

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
            
            if actuate: mouse.set_pwm(pwm_l, pwm_r)
            else: mouse.poll()
            
            s = mouse.get_sensors()
            
            stdscr.clear()
            stdscr.addstr(0, 0, "=== UCT Micromouse Co-Simulation Dashboard ===")
            stdscr.addstr(1, 0, "Connected! Steer with ARROWS. SPACE to brake. 'q' to quit.")
            stdscr.addstr(3, 0, f"Motor Intent : Left={pwm_l:<4} | Right={pwm_r:<4}")
            stdscr.addstr(4, 0, f"ToF Sensors  : L={s.get('tof_l',0):<4} | C={s.get('tof_c',0):<4} | R={s.get('tof_r',0):<4}")
            stdscr.addstr(5, 0, f"Battery      : {s.get('v_batt', 0.0):.2f} V")
            
            stdscr.addstr(7, 0, "-" * 60)
            stdscr.addstr(8, 0, f"RAW TX: {mouse.last_tx:<52}"[:60])
            stdscr.addstr(9, 0, f"RAW RX: {mouse.last_rx:<52}"[:60])
            stdscr.addstr(10, 0, "-" * 60)
            
            stdscr.refresh()
            time.sleep(0.05)
            
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
        if mouse and mouse.connected:
            mouse.set_pwm(0, 0)

if __name__ == "__main__":
    curses.wrapper(main)