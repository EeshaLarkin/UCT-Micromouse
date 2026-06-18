import uct_mouse

def run():
    if not uct_mouse.init():
        print("Failed to initialize mouse")
        return
        
    print("--- Test 2: Straight Line (Gyro Stabilized) & Stop before collision ---")
    
    heading_deg = 0.0
    dt_s = 0.05
    target_heading = 0.0
    
    try:
        while True:
            tof_l, tof_c, tof_r = uct_mouse.get_tof()
            gyro = uct_mouse.get_gyro()
            
            # Integrate gyro yaw rate to track heading
            heading_deg += gyro * dt_s
            print(f"Heading: {heading_deg:.2f} deg, ToF Center: {tof_c}mm")
            
            if tof_c < 150:
                print("Collision imminent! Stopping.")
                uct_mouse.set_motors(0, 0)
                break
                
            # Proportional controller on heading error to stay straight
            error = target_heading - heading_deg
            corr = error * 1.5
            
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
