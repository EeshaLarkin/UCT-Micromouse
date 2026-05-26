import time
from micromouse import Micromouse

def move_cells(mouse, cells, speed=40):
    """
    Moves the mouse forward by a given number of cells.
    Currently uses open-loop timing (Students: Upgrade this to use encoders or ToF!)
    """
    SECONDS_PER_CELL = 1.5 # Calibration constant
    duration = cells * SECONDS_PER_CELL
    
    print(f"Moving {cells} cells forward...")
    mouse.set_pwm(speed, speed)
    
    time.sleep(duration)
    
    mouse.set_pwm(0, 0)
    print("Move complete.\n")

def turn_deg(mouse, target_degrees, speed=40):
    """
    Turns the mouse in place by integrating the Z-axis gyroscope.
    """
    print(f"Turning {target_degrees} degrees...")
    
    # Determine spin direction
    if target_degrees > 0:
        mouse.set_pwm(speed, -speed)  # Spin right
    else:
        mouse.set_pwm(-speed, speed)  # Spin left

    target_angle = abs(target_degrees)
    current_angle = 0.0
    last_time = time.time()

    try:
        while current_angle < target_angle:
            mouse.poll()
            sensors = mouse.get_sensors()
            
            # Read the Z-axis rotational velocity (degrees per second)
            gyro_z = sensors.get('gyro', 0.0)
            
            # Calculate time delta
            now = time.time()
            dt = now - last_time
            last_time = now
            
            # Riemann Sum Integration: Angle = Sum(Velocity * Time)
            current_angle += abs(gyro_z * dt)
            
            time.sleep(0.01) # Run loop at ~100Hz
            
    finally:
        mouse.set_pwm(0, 0)
        print(f"Turn complete. Integrated angle: {current_angle:.1f} deg\n")

if __name__ == '__main__':
    # Connect to physical hardware (Switch to 'tcp' to connect to Simulink Autograder!)
    my_mouse = Micromouse(method='serial', verbose=True)
    my_mouse.connect()
    
    turn_deg(my_mouse, 90, speed=40)