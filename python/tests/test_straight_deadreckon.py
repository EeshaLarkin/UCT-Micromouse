import uct_mouse

def run():
    if not uct_mouse.init():
        print("Failed to initialize mouse")
        return
        
    print("--- Test 1: Straight Line (Dead Reckoning) & Stop before collision ---")
    
    # Run loop
    try:
        elapsed_time_ms = 0
        while True:
            tof_l, tof_c, tof_r = uct_mouse.get_tof()
            print(f"ToF Left: {tof_l}mm, Center: {tof_c}mm, Right: {tof_r}mm")
            
            # Stop if we are within 150mm of a wall ahead
            if tof_c < 150:
                print("Collision imminent! Stopping.")
                uct_mouse.set_motors(0, 0)
                break
                
            # Toggle between driving and stopping the motors every second
            if (elapsed_time_ms // 1000) % 2 == 0:
                # Drive straight using constant PWM (dead reckoning)
                uct_mouse.set_motors(40, 40)
            else:
                # Stop motors
                uct_mouse.set_motors(0, 0)
                
            uct_mouse.delay_ms(50)
            elapsed_time_ms += 50
            
    except KeyboardInterrupt:
        pass
        
    uct_mouse.set_motors(0, 0)
    print("Test Completed!")

if __name__ == "__main__":
    run()
