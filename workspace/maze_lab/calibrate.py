# =========================================================================
# calibrate.py  -  Measure the real mouse's constants for motion.py
# =========================================================================
# Lives in maze_lab (NOT part of the submission). Copy it to UCT_MMOUSE.
#
# Tests 1-3 (USB plugged in) - from the repo folder in PowerShell:
#     mpremote exec "import calibrate; calibrate.run(1)"
#   Results print in PowerShell. Nothing is written to the drive (writing
#   from the mouse while Windows has the drive open can corrupt it).
#
# Test 4 (spins 5 times - must be UNPLUGGED): make the drive's main.py
#     import calibrate
#     calibrate.run(4, to_file=True)
#   unplug, press RESET, then plug back in and open calib.txt.
#
# TESTS
#   1  Sensors   (motors OFF)  live ToF / gyro / encoder readout, ~45 s
#   2  Motors    (creeps ~5 cm) polarity, encoder signs, deadband per wheel
#   3  Straight  (drives ~40 cm toward a wall) ticks/m and speed per PWM
#   4  Spin      (5 turns in a dead-end cell) gyro scale + half axle length
# =========================================================================

import sys
import math
import uct_mouse

LOG_FILE = "calib.txt"
TO_FILE = False          # only write calib.txt when running unplugged (test 4)
LOOP_MS = 10
DT = 0.01

# Starting guesses - each test prints what to put in motion.py instead.
TICKS_PER_M = 5730.0
DEAD_BAND = 58.0


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if not TO_FILE:
        return
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def oled(row, text):
    try:
        uct_mouse.display_text(row, text[:18])
    except Exception:
        pass


def countdown(secs=3):
    """Time to take your hand away before the motors start."""
    for s in range(secs, 0, -1):
        oled(1, "Start in %d..." % s)
        uct_mouse.delay_ms(1000)
    oled(1, "Running")


def stop():
    uct_mouse.set_motors(0, 0)
    for _ in range(50):
        uct_mouse.delay_ms(LOOP_MS)


def gyro_bias(samples=200):
    total = 0.0
    for _ in range(samples):
        uct_mouse.delay_ms(LOOP_MS)
        total += uct_mouse.get_gyro()
    return total / samples


def avg_tof(samples=20):
    acc = [0.0] * 5
    for _ in range(samples):
        uct_mouse.delay_ms(LOOP_MS)
        t = uct_mouse.get_tof()
        for i in range(5):
            acc[i] += min(t[i], 2000)
    return [a / samples for a in acc]


# -------------------------------------------------------------------------
# Test 1: sensors only (motors OFF)
# -------------------------------------------------------------------------
def test_sensors(seconds=45):
    """Prints a reading every 0.5 s. While it runs:
      a) centre the mouse in a DEAD-END cell (walls left, front, right)
         -> which of the 5 ToF slots react? note the side + front values
      b) centre it in a cell with OPEN sides and front -> open readings
      c) rotate the mouse by hand ANTI-clockwise (lift it, don't roll it)
         -> gyro must read POSITIVE
    """
    say("=== TEST 1: sensors ===")
    bias = gyro_bias()
    say("gyro bias at rest: %+.3f deg/s" % bias)
    say("  ToF slots: (L, FL, C, FR, R) mm | gyro deg/s | encoders")
    for _ in range(seconds * 2):
        t = avg_tof(10)
        uct_mouse.delay_ms(400)
        g = uct_mouse.get_gyro() - bias
        l, r = uct_mouse.get_encoders()
        say("  %4d %4d %4d %4d %4d | %+7.1f | %d %d"
            % (t[0], t[1], t[2], t[3], t[4], g, l, r))
        oled(1, "L%d C%d R%d" % (t[0], t[2], t[4]))
        oled(2, "gyro %+.1f" % g)


# -------------------------------------------------------------------------
# Test 2: motor/encoder polarity and deadband
# -------------------------------------------------------------------------
def _ramp_one_wheel(side):
    """Raise one wheel's PWM until its encoder moves. Returns (pwm, ticks)."""
    l0, r0 = uct_mouse.get_encoders()
    for pwm in range(10, 101, 2):
        if side == 0:
            uct_mouse.set_motors(pwm, 0)
        else:
            uct_mouse.set_motors(0, pwm)
        for _ in range(15):                     # 150 ms at each PWM step
            uct_mouse.delay_ms(LOOP_MS)
        l, r = uct_mouse.get_encoders()
        moved = (l - l0) if side == 0 else (r - r0)
        if abs(moved) > 8:
            stop()
            return pwm, moved
    stop()
    return None, 0


def test_motors():
    """Mouse on the floor (or in the maze), lots of space around it.
    WATCH: in the last part both wheels push forward briefly - the mouse
    must move FORWARD (the ToF end first)."""
    say("=== TEST 2: motors, encoders, deadband ===")
    bias = gyro_bias()
    countdown()

    results = []
    for side, name in ((0, "LEFT"), (1, "RIGHT")):
        uct_mouse.delay_ms(500)
        pwm, moved = _ramp_one_wheel(side)
        results.append(pwm)
        say("%s wheel: starts moving at PWM %s, encoder change %+d %s"
            % (name, pwm, moved, "(OK)" if moved > 0 else "(NEGATIVE - flip encoder polarity)"))

    # One wheel only -> the mouse pivots. Left wheel forward = turn RIGHT (CW)
    # so the gyro must go NEGATIVE.
    uct_mouse.delay_ms(500)
    yaw = 0.0
    for _ in range(40):
        uct_mouse.set_motors(75, 0)
        uct_mouse.delay_ms(LOOP_MS)
        yaw += (uct_mouse.get_gyro() - bias) * DT
    stop()
    say("left wheel only -> gyro turned %+.1f deg %s"
        % (yaw, "(OK: clockwise is negative)" if yaw < 0 else "(SIGN WRONG - motion.py needs GYRO_SIGN = -1)"))

    uct_mouse.delay_ms(500)
    l0, r0 = uct_mouse.get_encoders()
    for _ in range(30):
        uct_mouse.set_motors(75, 75)
        uct_mouse.delay_ms(LOOP_MS)
    stop()
    l, r = uct_mouse.get_encoders()
    say("both wheels +75 for 0.3 s: encoders %+d %+d  -> did it move FORWARD? (look!)"
        % (l - l0, r - r0))

    ok = [p for p in results if p is not None]
    if ok:
        db = max(ok)
        say(">>> DEAD_BAND = %d   (left %s, right %s)" % (db, results[0], results[1]))
        oled(1, "DEADBAND %d" % db)


# -------------------------------------------------------------------------
# Test 3: drive straight toward a wall -> ticks per metre and speed
# -------------------------------------------------------------------------
def test_straight(pwm=75, dead_band=None, drive_m=0.40):
    """Centre the mouse in a straight corridor at least 3 cells long that
    ENDS IN A WALL, facing that wall. The front ToF measures the true
    distance travelled (start reading - end reading), the encoders count
    ticks over the same distance -> ticks per metre, no ruler needed."""
    if dead_band is None:
        dead_band = DEAD_BAND
    say("=== TEST 3: straight run, PWM %d ===" % pwm)
    d1 = avg_tof(30)[2]
    say("front wall at start: %.0f mm" % d1)
    if d1 > 1000:
        say("!! No wall seen ahead (needs < 1 m). Face a wall 2-4 cells away.")
        return
    bias = gyro_bias()
    countdown()

    l0, r0 = uct_mouse.get_encoders()
    target = drive_m * TICKS_PER_M
    yaw = 0.0
    speeds = []
    lp, rp = l0, r0
    for i in range(1000):
        # gentle heading hold so the ToF keeps pointing at the wall
        # yaw > 0 means we drifted left (CCW) -> speed up left, slow right
        corr = max(-10, min(10, 2.0 * yaw))
        uct_mouse.set_motors(int(pwm + corr), int(pwm - corr))
        uct_mouse.delay_ms(LOOP_MS)
        yaw += (uct_mouse.get_gyro() - bias) * DT
        l, r = uct_mouse.get_encoders()
        if i >= 40:                                       # skip the speed-up
            speeds.append(((l - lp) + (r - rp)) / 2.0 / DT)
        lp, rp = l, r
        if ((l - l0) + (r - r0)) / 2.0 >= target or uct_mouse.get_tof()[2] < 120:
            break
    stop()
    l, r = uct_mouse.get_encoders()
    ticks = ((l - l0) + (r - r0)) / 2.0
    d2 = avg_tof(30)[2]
    true_m = (d1 - d2) / 1000.0
    tpm = ticks / true_m if true_m > 0.05 else 0
    say("front wall at end: %.0f mm -> moved %.3f m, %d ticks" % (d2, true_m, ticks))
    if tpm:
        say(">>> TICKS_PER_M = %.0f" % tpm)
        if speeds:
            v = sum(speeds) / len(speeds) / tpm
            v_full = v * (100.0 - dead_band) / (pwm - dead_band)
            say("cruise speed at PWM %d: %.3f m/s" % (pwm, v))
            say(">>> V_AT_FULL = %.2f   (uses DEAD_BAND %d from test 2)" % (v_full, dead_band))
        oled(1, "TPM %.0f" % tpm)


# -------------------------------------------------------------------------
# Test 4: spin in a dead-end cell -> gyro scale and half-axle length
# -------------------------------------------------------------------------
def test_spin(turns=5, pwm=70):
    """Centre the mouse in a DEAD-END cell (walls left, front, right).
    It spins anticlockwise `turns` times. Each time the front ToF faces a
    wall squarely, its reading has a minimum - these happen exactly 90 deg
    apart (180 deg across the open side). Comparing the gyro angle between
    the first and last minimum with the true multiple of 90 deg gives the
    gyro scale. Encoders over the same rotation give the half-axle length."""
    say("=== TEST 4: spin x%d ===" % turns)
    bias = gyro_bias()
    countdown()

    yaw = 0.0
    l0, r0 = uct_mouse.get_encoders()
    hist = []                                    # (yaw, front_tof)
    while yaw < 360.0 * turns + 30:
        uct_mouse.set_motors(-pwm, pwm)
        uct_mouse.delay_ms(LOOP_MS)
        yaw += (uct_mouse.get_gyro() - bias) * DT
        hist.append((yaw, uct_mouse.get_tof()[2]))
        if len(hist) > 6000:
            break
    stop()
    l, r = uct_mouse.get_encoders()

    # Find the dips in the front reading (front ToF close to a wall).
    # Noise can split one dip into fragments, so readings below `near` are
    # grouped while they're within 20 deg of each other. Neighbouring walls
    # may merge into one wide dip - that's fine: what matters is that the
    # SAME dip comes back once per revolution, so any fixed offset cancels.
    n = len(hist)
    groups = []                                  # [first_yaw, last_yaw]
    # real sensors read ~45 mm high (test 1: dead-end front = 75 mm)
    near = 140 if sys.implementation.name == "micropython" else 100
    for yw, d in hist:
        if d < near:
            if groups and yw - groups[-1][1] < 20.0:
                groups[-1][1] = yw
            else:
                groups.append([yw, yw])
    mins = [(g0 + g1) / 2.0 for g0, g1 in groups if g1 - g0 > 5.0]
    if len(mins) < 4:
        say("!! Only %d wall minima seen - is the mouse centred in a dead end?" % len(mins))
        return

    true_total = 0
    for k in range(1, len(mins)):
        true_total += 90 * max(1, round((mins[k] - mins[k - 1]) / 90.0))
    gyro_total = mins[-1] - mins[0]
    scale = true_total / gyro_total
    # quality: every gap, rescaled, should land on a multiple of 90 deg
    worst = 0.0
    for k in range(1, len(mins)):
        g = (mins[k] - mins[k - 1]) * scale
        worst = max(worst, abs(g - 90 * round(g / 90.0)))
    say("wall dips: %d, gyro saw %.1f deg, true rotation %d deg, worst misfit %.1f deg"
        % (len(mins), gyro_total, true_total, worst))
    if worst > 10:
        say("!! Dips are inconsistent - re-centre the mouse in the dead end and repeat")
    say(">>> GYRO_SCALE = %.4f   (true deg per gyro deg)" % scale)

    true_rad = math.radians(yaw * scale)
    arc_m = ((r - r0) - (l - l0)) / 2.0 / TICKS_PER_M
    half_axle = arc_m / true_rad
    say(">>> HALF_AXLE_M = %.4f  (with TICKS_PER_M %.0f)" % (half_axle, TICKS_PER_M))
    oled(1, "GS %.3f" % scale)
    oled(2, "HA %.4f" % half_axle)


def run(test, to_file=False):
    global TICKS_PER_M, DEAD_BAND, TO_FILE
    TO_FILE = to_file
    if sys.implementation.name != "micropython":   # PC simulator check-run
        TICKS_PER_M, DEAD_BAND = 4400.0, 28.0
    if not uct_mouse.init():
        print("init failed")
        return
    try:
        with open("polarity.txt") as f:
            p = [int(v) for v in f.read().strip().split(",")]
        uct_mouse.set_polarity(p[0], p[1])
        if len(p) >= 4:
            uct_mouse.set_encoder_polarity(p[2], p[3])
        say("polarity.txt:", p)
    except Exception:
        uct_mouse.set_polarity(1, 1)
        say("no polarity.txt - using set_polarity(1, 1)")
    uct_mouse.delay_ms(50)
    (None, test_sensors, test_motors, test_straight, test_spin)[test]()
    uct_mouse.set_motors(0, 0)
    say("done")
