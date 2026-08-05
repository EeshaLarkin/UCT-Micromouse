import uct_mouse
import time

class PIDController:
    def __init__(self, kp, ki, kd, max_out=100, min_out=-100):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_out = max_out
        self.min_out = min_out
        
        self.prev_error = 0
        self.integral = 0

    def compute(self, target, actual, dt):
        error = target - actual
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = error
        
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        if output > self.max_out:
            output = self.max_out
            self.integral -= error * dt  # Anti-windup clamping
        elif output < self.min_out:
            output = self.min_out
            self.integral -= error * dt  # Anti-windup clamping
            
        return output

    def reset(self):
        self.prev_error = 0
        self.integral = 0


class WheelVelocityController:
    def __init__(self, kp=1.2, ki=0.5, kd=0.05, max_pwm=100):
        # Two independent PID controllers
        self.pid_l = PIDController(kp, ki, kd, max_out=max_pwm, min_out=-max_pwm)
        self.pid_r = PIDController(kp, ki, kd, max_out=max_pwm, min_out=-max_pwm)
        
        # Keep track of target speeds (ticks per interval)
        self.target_l = 0.0
        self.target_r = 0.0
        
        # Keep track of previous encoder readings
        self.prev_enc_l = None
        self.prev_enc_r = None
        
        # Keep track of step timing for dynamic dt calculations
        self.last_step_time = None

    def set_targets(self, left_target, right_target):
        """Set the target velocities for the wheels (in ticks per interval)."""
        self.target_l = left_target
        self.target_r = right_target

    def step(self, dt=None):
        """
        Highest-level control interface. 
        Automatically reads encoders, runs the PID calculation, and writes 
        motor actuation values.
        If dt is omitted, it calculates elapsed time dynamically using system clock.
        """
        # 1. Automatically fetch raw encoder values
        left_enc, right_enc = uct_mouse.get_encoders()
        
        # 2. Calculate dynamic dt if not explicitly passed
        current_time = time.time()
        if dt is None:
            if self.last_step_time is None:
                dt = 0.05  # Standard fallback for the first step (50ms)
            else:
                dt = current_time - self.last_step_time
            self.last_step_time = current_time
            if dt <= 0:
                dt = 0.001  # Prevent division-by-zero bounds
        else:
            self.last_step_time = current_time
            
        # 3. Delegate to the core update logic
        return self.update(left_enc, right_enc, dt)

    def update(self, current_enc_l, current_enc_r, dt):
        """
        Core control step. Useful if you want to feed custom encoder values 
        manually (e.g. during simulations or filtering).
        """
        # If this is the very first run, initialize the encoder history
        if self.prev_enc_l is None or self.prev_enc_r is None:
            self.prev_enc_l = current_enc_l
            self.prev_enc_r = current_enc_r
            return (0.0, 0.0)

        # 1. Calculate actual velocity (change in ticks since the last update)
        actual_l = current_enc_l - self.prev_enc_l
        actual_r = current_enc_r - self.prev_enc_r
        
        # 2. Update encoder history
        self.prev_enc_l = current_enc_l
        self.prev_enc_r = current_enc_r
        
        # 3. Compute control output (PWM)
        pwm_l = self.pid_l.compute(self.target_l, actual_l, dt)
        pwm_r = self.pid_r.compute(self.target_r, actual_r, dt)
        
        # 4. Actuate the hardware
        uct_mouse.set_motors(int(pwm_l), int(pwm_r))
        
        return (pwm_l, pwm_r)

    def stop(self):
        """Helper to instantly halt the motors and reset controller integrators."""
        self.set_targets(0.0, 0.0)
        self.pid_l.reset()
        self.pid_r.reset()
        self.prev_enc_l = None
        self.prev_enc_r = None
        uct_mouse.set_motors(0, 0)


def main():
    uct_mouse.init()
    
    # Create the high-level velocity controller
    controller = WheelVelocityController(kp=1.2, ki=0.5, kd=0.05)
    
    # Configure target speeds (ticks per 50ms)
    controller.set_targets(left_target=40.0, right_target=40.0)
    
    loop_period_ms = 50
    
    print("Starting abstracted closed-loop controller demo...")
    
    for i in range(100):
        start_time = time.time()
        
        # Runs the highest-level step (automatically reads encoders, calculates dt, and writes PWM)
        pwm_l, pwm_r = controller.step()
        
        print(f"Step {i:3d} | Output PWM: L={pwm_l:5.1f}, R={pwm_r:5.1f}")
        
        # Keep loop timing steady
        elapsed = (time.time() - start_time) * 1000
        sleep_time = max(0, loop_period_ms - elapsed)
        uct_mouse.delay_ms(int(sleep_time))

    # Safely halt
    controller.stop()
    print("Run complete. Motors stopped.")

if __name__ == "__main__":
    main()
