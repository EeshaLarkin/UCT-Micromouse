# =========================================================================
# UCT Micromouse - Milestone 1: Run a Square (1m x 1m) (Framework)
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

def calibrate_gyro():
    """
    Calibrates the gyroscope Z-axis bias while the mouse is stationary.
    Collects 100 samples over 1.0 second (10ms intervals) to calculate average bias.
    """
    global GYRO_BIAS
    print("  [Calibrating Gyro] Please keep the mouse still...")
    
    uct_mouse.set_motors(0, 0)
    
    # Sensor warm-up: let socket connection and telemetry stream stabilize (200ms)
    for _ in range(20):
        uct_mouse.delay_ms(10)
        
    GYRO_BIAS = 0.0  # Zero out bias during calibration run
    samples = []
    for _ in range(100):  # 100 samples at 10ms = 1.0 second
        uct_mouse.delay_ms(10)
        samples.append(uct_mouse.get_gyro())
        
    GYRO_BIAS = sum(samples) / len(samples)
    print(f"  [Calibrating Gyro] Complete. Estimated bias: {GYRO_BIAS:.4f} dps")

def drive_straight(distance_m):
    """
    TODO: Implement closed-loop straight line control.
    Use encoder counts to measure distance, and gyroscope Z-axis angular rate
    (gyro) to correct heading drift.
    """
    print(f"Driving straight for {distance_m}m...")
    # Student code here
    # Example (open-loop, prone to errors):
    # uct_mouse.set_motors(50, 50)
    # uct_mouse.delay_ms(1500)
    # uct_mouse.set_motors(0, 0)
    pass

def turn_left_90():
    """
    TODO: Implement closed-loop turning control.
    Use the gyroscope Z-axis angular rate (gyro) to integrate heading angle
    and turn exactly 90 degrees counter-clockwise.
    """
    print("Turning 90 degrees left...")
    # Student code here
    # Example (open-loop, prone to errors):
    # uct_mouse.set_motors(-35, 35)
    # uct_mouse.delay_ms(600)
    # uct_mouse.set_motors(0, 0)
    pass

def run_square():
    if not uct_mouse.init():
        print("Initialization failed.")
        return

    # Load polarity calibration if it exists
    try:
        with open("polarity.txt", "r") as f:
            lines = f.read().strip().split(",")
            uct_mouse.set_polarity(int(lines[0]), int(lines[1]))
            if len(lines) >= 4:
                uct_mouse.set_encoder_polarity(int(lines[2]), int(lines[3]))
    except Exception:
        uct_mouse.set_polarity(-1, -1)

    print("--- Milestone 1: Run a Square ---")

    for side in range(4):
        # 1. Drive forward 1 meter
        drive_straight(1.0)
        
        # 2. Settle briefly
        uct_mouse.set_motors(0, 0)
        uct_mouse.delay_ms(200)
        
        # 3. Turn 90 degrees left
        turn_left_90()
        
        # 4. Settle briefly
        uct_mouse.set_motors(0, 0)
        uct_mouse.delay_ms(200)

    print("Milestone 1 Completed!")

if __name__ == "__main__":
    run_square()
