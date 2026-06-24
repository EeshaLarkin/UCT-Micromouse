# =========================================================================
# UCT Micromouse - Milestone 1: Run a Square (1m x 1m)
# =========================================================================
# ASSIGNMENT DESCRIPTION:
# Implement a control loop to drive the mouse in a 1 meter by 1 meter square,
# turning 90 degrees at each corner, and returning to the start position.
# 
# KEY CONTROLS:
# - uct_mouse.set_motors(left_pwm, right_pwm) -> Set speed (-100 to 100)
# - uct_mouse.get_encoders() -> Returns (left_ticks, right_ticks)
# - uct_mouse.get_tof()      -> Returns (left_mm, center_mm, right_mm)
# - uct_mouse.delay_ms(ms)   -> Suspends execution and updates sensors
#
# GRADING:
# - The autograder applies 8% motor imbalance and 8% wheel slip.
# - Open-loop timing alone will accumulate errors. Use encoder and gyro
#   feedback to compensate.
# =========================================================================

import uct_mouse
import math

TICK_DIST_M = (2.0 * math.pi * 0.031) / 8.0

def run_square():
    if not uct_mouse.init():
        print("Initialization failed.")
        return

    try:
        with open("polarity.txt", "r") as f:
            lines = f.read().strip().split(",")
            uct_mouse.set_polarity(int(lines[0]), int(lines[1]))
    except Exception:
        uct_mouse.set_polarity(1, 1)

    print("--- Milestone 1: Run a Square ---")

    heading_deg = 0.0
    dt_s = 0.05
    target_heading = 0.0

    def delay_and_track(ms):
        nonlocal heading_deg
        accumulated = 0
        while accumulated < ms:
            step = min(50, ms - accumulated)
            uct_mouse.delay_ms(step)
            accumulated += step
            sensors = uct_mouse._mouse.get_sensors()
            gyro = sensors.get('gyro', 0.0)
            heading_deg += gyro * (step / 1000.0)

    for side in range(4):
        print(f"Driving side {side + 1}...")
        lenc_start, renc_start = uct_mouse.get_encoders()
        
        # Step 1: Drive forward 1m
        while True:
            sensors = uct_mouse._mouse.get_sensors()
            gyro = sensors.get('gyro', 0.0)
            heading_deg += gyro * dt_s
            
            lenc, renc = uct_mouse.get_encoders()
            dist = ((lenc - lenc_start) + (renc - renc_start)) / 2.0 * TICK_DIST_M
            
            if dist >= 1.04: # average 4% slip
                break
                
            diff = target_heading - heading_deg
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            
            corr = diff * 1.5
            l_pwm = 50 - corr
            r_pwm = 50 + corr
            uct_mouse.set_motors(max(20, min(80, l_pwm)), max(20, min(80, r_pwm)))
            uct_mouse.delay_ms(50)
            
        uct_mouse.set_motors(0, 0)
        delay_and_track(200)
        
        # Step 2: Turn 90 degrees (Left turn to avoid border walls)
        print(f"Turning corner {side + 1}...")
        target_heading += 90.0
        
        while True:
            sensors = uct_mouse._mouse.get_sensors()
            gyro = sensors.get('gyro', 0.0)
            heading_deg += gyro * dt_s
            
            diff = target_heading - heading_deg
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            
            if abs(diff) < 2.0:
                break
                
            pwm = 35
            if abs(diff) < 20: pwm = 20
            
            # Since target_heading increased, diff is positive, so we want to turn left
            if diff > 0:
                uct_mouse.set_motors(-pwm, pwm)
            else:
                uct_mouse.set_motors(pwm, -pwm)
            uct_mouse.delay_ms(50)
                
        uct_mouse.set_motors(0, 0)
        delay_and_track(200)

    print("Milestone 1 Completed!")

if __name__ == "__main__":
    run_square()
