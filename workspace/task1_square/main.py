# =========================================================================
# UCT Micromouse - Milestone 1: Run a Square (1m x 1m) (Framework)
# =========================================================================

import uct_mouse
import math

TICKS_PER_M = 5730
RUN_TIME_MS = 6000        # runs for 6 seconds
LOOP_MS = 10
BASE_SPEED = 85
KP_BALANCE = 3 

KP_HEADING = 1.5
KI_HEADING = 0.05
KD_HEADING = 0.3
GYRO_BIAS = 0.0

I_HEADING_LIM = 10
OUTPUT_LIM = 15
TURN_OUTPUT_LIM = 70

TURN_TARGET_DEG = 90.0
ANGLE_GAIN = 0.89
ON_HARDWARE = False
TURN_TOLERANCE_DEG = 1.0
SETTLE_LOOPS_REQ = 5
MIN_TURN_PWM = 67

KP_TURN = 1.25
KD_TURN = 0.25

# Complementary Filter Parameters
TRUST = 1 #0.95
ENC_HEADING_SCALE = 0.01


# Clamp to stay within range
def clamp(value, low, high):
    return max(low, min(value, high))


def _sensor():
    # Returns sensor values and subtracts gyro bias
    lenc, renc = uct_mouse.get_encoders()
    gyro = uct_mouse.get_gyro() - GYRO_BIAS
    return lenc, renc, gyro


class PID:
    def __init__(self, kp, ki, kd, I_lim, output_lim):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.I_lim = I_lim
        self.output_lim = output_lim
        self.integral = 0.0
        self.prev_error = 0.0

    def pid_output(self, error, dt_s):
        # Integral
        self.integral = clamp(self.integral + (error * dt_s), -self.I_lim, self.I_lim)
        # Derivative
        derivative = (error - self.prev_error)/dt_s
        self.prev_error = error

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        return clamp(output, -self.output_lim, self.output_lim)


def calibrate_gyro():
    """
    Calibrates the gyroscope Z-axis bias while the mouse is stationary.
    """
    global GYRO_BIAS
    
    uct_mouse.set_motors(0, 0)
    
    for _ in range(20):
        uct_mouse.delay_ms(10)
        
    GYRO_BIAS = 0.0 
    samples = []
    for _ in range(100): 
        uct_mouse.delay_ms(10)
        samples.append(uct_mouse.get_gyro())
        
    GYRO_BIAS = sum(samples) / len(samples)
    print(f"  [Calibrating Gyro] Complete. Estimated bias: {GYRO_BIAS:.4f} dps")


def drive_straight(distance_m):
    target_ticks = int(distance_m * TICKS_PER_M)
    print(f"Driving straight for {distance_m}m...")

    heading_pid = PID(KP_HEADING, KI_HEADING, KD_HEADING, I_HEADING_LIM, OUTPUT_LIM)
    start_l, start_r, _ = _sensor()

    lenc0, renc0 = start_l, start_r
    time_elapsed = 0
    total_l, total_r = 0, 0
    dt = 0.01
    heading_deg = 0.0

    while time_elapsed <= RUN_TIME_MS:
        lenc1, renc1, gyro_rate = _sensor()
        dl = lenc1 - lenc0
        dr = renc1 - renc0
        lenc0, renc0 = lenc1, renc1
        total_l += dl
        total_r += dr

        avg = ((lenc1 - start_l) + (renc1 - start_r))/2.0
        if avg >= target_ticks:
            break

        # P-controller error correction for straight line balance
        cross_error = dl - dr
        enc_c = KP_BALANCE * cross_error

        # Complementary Filter for Heading
        gyro_estimate = gyro_rate * dt
        encoder_estimate = (dr - dl) * ENC_HEADING_SCALE
        fused_heading_change = (TRUST * gyro_estimate) + ((1.0 - TRUST) * encoder_estimate)
        heading_deg += fused_heading_change

        heading_error = 0.0 - heading_deg
        head_c = heading_pid.pid_output(heading_error, dt)
        
        correction = enc_c + head_c
        
        left_pwm = clamp(BASE_SPEED - correction, -100, 100)
        right_pwm = clamp(BASE_SPEED + correction, -100, 100)
        uct_mouse.set_motors(int(left_pwm), int(right_pwm))
        
        uct_mouse.delay_ms(LOOP_MS)
        time_elapsed += LOOP_MS

    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(LOOP_MS)


def turn_left_90():
    turn_pid = PID(KP_TURN, 0.0, KD_TURN, 1.0, TURN_OUTPUT_LIM)
    lenc0, renc0, _ = _sensor()
    heading_deg = 0.0
    dt = 0.01
    time_elapsed = 0
    settle_count = 0

    if ON_HARDWARE:
        turn_target = TURN_TARGET_DEG * ANGLE_GAIN
    else:
        turn_target = TURN_TARGET_DEG

    while time_elapsed <= RUN_TIME_MS:
        lenc1, renc1, gyro_rate = _sensor()
        dl = lenc1 - lenc0
        dr = renc1 - renc0
        lenc0, renc0 = lenc1, renc1

        # Complementary Filter during turns
        gyro_estimate = gyro_rate * dt
        encoder_estimate = (dr - dl) * ENC_HEADING_SCALE
        fused_heading_change = (TRUST * gyro_estimate) + ((1.0 - TRUST) * encoder_estimate)
        heading_deg += fused_heading_change

        heading_error = turn_target - heading_deg

        if abs(heading_error) < TURN_TOLERANCE_DEG:
            settle_count += 1
            uct_mouse.set_motors(0, 0)
            if settle_count >= SETTLE_LOOPS_REQ:
                break

        else:
            settle_count = 0
            output = turn_pid.pid_output(heading_error, dt)

            if 0 < abs(output) < MIN_TURN_PWM:
                output = MIN_TURN_PWM if output > 0 else -MIN_TURN_PWM

            left_pwm = clamp(-output, -100, 100)
            right_pwm = clamp(output, -100, 100)
            uct_mouse.set_motors(int(left_pwm), int(right_pwm))

        uct_mouse.delay_ms(LOOP_MS)
        time_elapsed += LOOP_MS

    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(LOOP_MS)


def run_square():
    if not uct_mouse.init():
        print("Initialization failed.")
        return

    try:
        with open("polarity.txt", "r") as f:
            lines = f.read().strip().split(",")
            uct_mouse.set_polarity(int(lines[0]), int(lines[1]))
            if len(lines) >= 4:
                uct_mouse.set_encoder_polarity(int(lines[2]), int(lines[3]))
    except Exception:
        uct_mouse.set_polarity(-1, -1)

    calibrate_gyro()

    for side in range(4):
        drive_straight(1.0)
        turn_left_90()

    drive_straight(0.05)


if __name__ == "__main__":
    run_square()