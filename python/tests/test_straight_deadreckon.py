import uct_mouse

def run():
    if not uct_mouse.init():
        print("Failed to initialize mouse")
        return
        
    print("--- Test 1: Straight Line (Dead Reckoning) & Stop before collision ---")
    uct_mouse.delay_ms(200)
    
    # Run loop
    try:
        elapsed_time_ms = 0
        while True:
            tof_l, tof_al, tof_c, tof_ar, tof_r = uct_mouse.get_tof()
            print("ToF Left:", tof_l, "Center:", tof_c, "Right:", tof_r)
            
            # Stop if we are within 150mm of a wall ahead
            if tof_c < 150:
                print("Collision imminent! Stopping.")
                uct_mouse.set_motors(0, 0)
                break
                
            # Toggle between driving and stopping the motors every second
            if (elapsed_time_ms // 1000) % 2 == 0:
                # Drive straight using constant PWM (dead reckoning)
                uct_mouse.set_motors(80, 80)
            else:
                # Stop motors
                uct_mouse.set_motors(0, 0)
                
            uct_mouse.delay_ms(50)
            elapsed_time_ms += 50
            
    except Exception as e:
        print("Python Exception: ")
        print(e)
    except KeyboardInterrupt:
        pass
        
    uct_mouse.set_motors(0, 0)
    print("Test Completed!")

# Define __name__ if running under PikaScript which lacks it
try:
    __name__
except NameError:
    __name__ = "__main__"

if __name__ == "__main__":
    run()
