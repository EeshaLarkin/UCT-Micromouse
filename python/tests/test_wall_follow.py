import uct_mouse

def run():
    if not uct_mouse.init():
        print("Failed to initialize mouse")
        return
        
    print("--- Test 3: Wall Following & Stop before collision ---")
    
    # Read initial distances to choose which wall to follow
    # Give it a moment to initialize and settle
    uct_mouse.delay_ms(100)
    tof_l, tof_al, tof_c, tof_ar, tof_r = uct_mouse.get_tof()
    
    # Choose which wall to follow based on whichever we started closer to
    if tof_l < tof_r:
        side = "left"
        target_dist = tof_l
        print(f"Following LEFT wall. Target distance: {target_dist}mm")
    else:
        side = "right"
        target_dist = tof_r
        print(f"Following RIGHT wall. Target distance: {target_dist}mm")
        
    try:
        while True:
            tof_l, tof_al, tof_c, tof_ar, tof_r = uct_mouse.get_tof()
            print(f"ToF L: {tof_l}mm, C: {tof_c}mm, R: {tof_r}mm")
            
            if tof_c < 150:
                print("Collision imminent! Stopping.")
                uct_mouse.set_motors(0, 0)
                break
                
            # Drive straight, correcting distance to side wall
            if side == "left":
                error = target_dist - tof_l
                corr = error * 0.4
                l_pwm = int(40 + corr)
                r_pwm = int(40 - corr)
            else:
                error = target_dist - tof_r
                corr = error * 0.4
                l_pwm = int(40 - corr)
                r_pwm = int(40 + corr)
                
            # Clamp PWM values to safe limits
            l_pwm = max(15, min(75, l_pwm))
            r_pwm = max(15, min(75, r_pwm))
            
            uct_mouse.set_motors(l_pwm, r_pwm)
            uct_mouse.delay_ms(50)
            
    except KeyboardInterrupt:
        pass
        
    uct_mouse.set_motors(0, 0)
    print("Test Completed!")

if __name__ == "__main__":
    run()
