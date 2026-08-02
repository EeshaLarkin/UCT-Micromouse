import uct_mouse
import sys

def main():
    # Initialize the connection to PC Simulator or Physical Hardware
    # This also re-initializes the SSD1306 OLED and VL53L0X ToF sensors on physical boot.
    uct_mouse.init()
    uct_mouse.set_polarity(1, 1)
    
    print("--- UCT Mouse Idle Telemetry Test ---")
    
    while True:
        # Read sensor values
        tof_l, tof_al, tof_c, tof_ar, tof_r = uct_mouse.get_tof()
        gyro = uct_mouse.get_gyro()
        vbatt = uct_mouse.get_vbatt()
        lenc, renc = uct_mouse.get_encoders()
        
        # Print telemetry frames to standard output (readable via serial VCP)
        print("ToF: L={:<4} C={:<4} R={:<4} | Gyro: {:<6.3f} | Batt: {:<4.2f}V | Enc: L={:<5} R={:<5}".format(
            tof_l, tof_c, tof_r, gyro, vbatt, lenc, renc
        ))
        
        # update display and wait 100ms (sensor registers refresh inside delay_ms)
        uct_mouse.delay_ms(100)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            uct_mouse.set_motors(0, 0)
        except:
            pass
        
        # Log error to file for untethered debugging
        try:
            with open('error_log.txt', 'w') as f:
                sys.print_exception(e, f)
        except:
            pass
        raise e
