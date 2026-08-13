# =========================================================================
# UCT Micromouse - Milestone 0: Run Straight (Reference)
# =========================================================================
# ALGORITHM:
#   Drive forward for a fixed distance (e.g., 2.0 metres) using
#   closed-loop feedback.
#
#   Straight phase  — Fused encoder + gyro control.
#       Encoder balance (P-controller) compensates for motor speed asymmetry.
#       Gyro heading integration corrects residual drift that encoder-only
#       control cannot eliminate (steady-state P-error + wheel slip).
#       Both corrections are summed into each motor PWM command.
#
# =========================================================================

import uct_mouse

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
DISTANCE_M      = 1.00          # metres to drive straight
TICKS_PER_M     = 41            # encoder ticks per metre — matches simulator
TARGET_TICKS    = int(DISTANCE_M * TICKS_PER_M)

FWD_PWM         = 45            # base forward PWM (–100 … 100)

KP_BALANCE      = 0.5           # P-gain: corrects left/right encoder imbalance during straight
KH_HEADING      = 1.5           # P-gain: corrects accumulated heading drift via gyro integration

VERBOSE         = True          # print debug info during run

# ---------------------------------------------------------------------------
# Helpers to read sensors cleanly
# ---------------------------------------------------------------------------

def _sensors():
    """Returns (lenc, renc, gyro_dps) from the current shadow state."""
    lenc, renc = uct_mouse.get_encoders()
    gyro = uct_mouse.get_gyro()   # gyro Z-axis in degrees/second
    return lenc, renc, gyro

# ---------------------------------------------------------------------------
# Movement primitive: drive straight
# ---------------------------------------------------------------------------

def drive_straight(distance_m: float):
    """
    Drive forward exactly distance_m metres using fused encoder + gyro control.
    """
    lenc0, renc0, _ = _sensors()
    target = int(distance_m * TICKS_PER_M)
    dt_s   = 0.050          # physics step (20 Hz simulator)
    heading_drift = 0.0     # accumulated heading error in degrees (+ = drifting CCW/left)

    if VERBOSE:
        print("Driving %f m  (target %d ticks)..." % (distance_m, target))

    while True:
        lenc, renc, gyro_dps = _sensors()
        dl = lenc - lenc0
        dr = renc - renc0
        avg = (dl + dr) / 2.0

        if avg >= target:
            break

        # Integrate heading drift (CCW = positive gyro = curving left)
        heading_drift += gyro_dps * dt_s

        # Term 1: encoder balance — keeps arc lengths equal
        cross_error = dl - dr
        enc_correction = KP_BALANCE * cross_error

        # Term 2: gyro heading — drives heading drift back to zero
        #   drift > 0 → curving left → increase right, decrease left
        heading_correction = KH_HEADING * heading_drift

        l_pwm = int(FWD_PWM - enc_correction + heading_correction)
        r_pwm = int(FWD_PWM + enc_correction - heading_correction)

        # Clamp to safe range
        l_pwm = max(15, min(75, l_pwm))
        r_pwm = max(15, min(75, r_pwm))

        uct_mouse.set_motors(l_pwm, r_pwm)
        uct_mouse.delay_ms(50)  # Refresh sensors and update the OLED screen!

    # Hard stop
    uct_mouse.set_motors(0, 0)
    lenc_f, renc_f, _ = _sensors()
    if VERBOSE:
        dl_f = lenc_f - lenc0
        dr_f = renc_f - renc0
        print("Done. Ticks L=%d  R=%d  imbalance=%d ticks  heading_drift=%.1f°" %
              (dl_f, dr_f, abs(dl_f-dr_f), heading_drift))

    uct_mouse.delay_ms(120)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_straight():
    if not uct_mouse.init():
        print("Initialization failed.")
        return

    # Default polarity configurations must be hardcoded in code rather than read from external files
    uct_mouse.set_polarity(1, 1)

    print("=== Milestone 0: Run Straight ===")
    print("  Encoder target : %d ticks  (%d ticks/m)" % (TARGET_TICKS, TICKS_PER_M))
    print()

    drive_straight(DISTANCE_M)

    # Final stop
    uct_mouse.set_motors(0, 0)
    print()
    print("=== Milestone 0 Complete! ===")

try:
    __name__
except NameError:
    __name__ = "__main__"

if __name__ == "__main__":
    run_straight()
