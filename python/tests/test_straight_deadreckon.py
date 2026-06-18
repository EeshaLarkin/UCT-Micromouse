import uct_mouse

def run():
    if not uct_mouse.init():
        print("Failed to initialize mouse")
        return
        
    print("--- Test 1: Straight Line (Dead Reckoning) & Stop before collision ---")
    
    # Run loop
    try:
        while True:
            tof_l, tof_c, tof_r = uct_mouse.get_tof()
            print(f"ToF Left: {tof_l}mm, Center: {tof_c}mm, Right: {tof_r}mm")
            
            # Stop if we are within 150mm of a wall ahead
            if tof_c < 150:
                print("Collision imminent! Stopping.")
                uct_mouse.set_motors(0, 0)
                break
                
            # Drive straight using constant PWM (dead reckoning)
            uct_mouse.set_motors(40, 40)
            uct_mouse.delay_ms(50)
            
    except KeyboardInterrupt:
        pass
        
    uct_mouse.set_motors(0, 0)
    print("Test Completed!")

if __name__ == "__main__":
    run()
