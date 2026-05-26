import PikaStdLib
import uct_mouse

print('=== UCT Micromouse Wall Follower (Standalone) ===')
mouse = uct_mouse.Mouse()

BASE_SPEED = 40
Kp = 0.5  

while True:
    # 1. Instruct the C-Kernel to fire sensors & sleep 50ms
    mouse.tick()
    
    # 2. Read sensors natively
    tof_l = mouse.get_tof_l()
    tof_r = mouse.get_tof_r()
    
    # 3. Calculate error
    error = tof_l - tof_r
    correction = int(error * Kp)
    
    # 4. Apply correction
    left_speed = BASE_SPEED - correction
    right_speed = BASE_SPEED + correction
    
    # Clamp speeds explicitly (safe for lightweight Python engines)
    if left_speed > 100: left_speed = 100
    if left_speed < 0: left_speed = 0
    if right_speed > 100: right_speed = 100
    if right_speed < 0: right_speed = 0
    
    # 5. Actuate & Log
    mouse.set_pwm(left_speed, right_speed)
    print('L:', tof_l, '| R:', tof_r, '| Err:', error)
