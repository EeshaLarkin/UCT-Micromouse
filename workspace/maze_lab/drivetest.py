# =========================================================================
# drivetest.py  -  First real driving tests of motion.py on the maze
# =========================================================================
# Upload with build_robot.py (--extra workspace/maze_lab/drivetest.py), then:
#
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.move(1)"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.move(2)"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.turns(1, 4)"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.turns(-1, 4)"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.pirouette()"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.sensors()"
#   python -m mpremote connect COM6 resume exec "import drivetest; drivetest.clock()"
#
# Each test: 3 s countdown on the OLED, gyro calibration (keep still), the
# move, then a report. Motors are always switched off, even on an error.
# =========================================================================

import uct_mouse
import motion


def _setup():
    uct_mouse.init()
    uct_mouse.set_polarity(1, 1)
    uct_mouse.set_motors(0, 0)
    for s in (3, 2, 1):
        try:
            uct_mouse.display_text(1, "Start in %d..." % s)
        except Exception:
            pass
        uct_mouse.delay_ms(1000)
    m = motion.Motion()
    m.calibrate_gyro()
    return m


def _print_log(m):
    """Every 3rd control tick of the last move, plus the final ticks."""
    lg = m.log
    if not lg:
        return
    n = len(lg) // 5
    print("  tick  v_cmd  v_real  front  pwmL  pwmR   (speeds mm/s, front mm)")
    for i in range(n):
        if i % 3 == 0 or i >= n - 6:
            k = 5 * i
            print("  %4d  %5d  %6d  %5d  %4d  %4d"
                  % (i, lg[k], lg[k + 1], lg[k + 2], lg[k + 3], lg[k + 4]))


def _report(m, label):
    l, f, r = m.read_walls()
    print("%s done in %.1f s" % (label, m.dt_sum))
    print("  ToF now  L %d  C %d  R %d   (centred: sides ~100, dead-end front ~40)"
          % (m.tof_l, m.tof_c, m.tof_r))
    print("  walls seen  left %s  front %s  right %s" % (l, f, r))
    print("  heading error %+.1f deg   wall heading correction %+.1f deg"
          % (m.target_yaw - m.yaw(), m.yaw_corr))
    print("  odometry scale %.3f   wall-edge fixes %d   emergency stops %d   stalls %d"
          % (m.odo_scale, m.edge_fixes, m.emergency_stops, m.stalls))
    print("  bump recoveries %d   overrun stops %d" % (m.unsticks, m.overruns))
    try:
        print("  battery %.2f V" % uct_mouse.get_vbatt())
    except Exception:
        pass
    if m.turns_done:
        print("  turns: %d, mean error %.1f deg, worst %.1f deg"
              % (m.turns_done, m.turn_err_sum / m.turns_done, m.turn_err_max))


def move(cells=1, v=0.16):
    """Drive `cells` cells straight and stop at the centre."""
    m = None
    try:
        m = _setup()
        m.log = []
        m.move(cells, v_max=v, accel=0.8)
        uct_mouse.set_motors(0, 0)
        _report(m, "move(%d)" % cells)
        _print_log(m)
    finally:
        uct_mouse.set_motors(0, 0)


def turns(quarter=1, count=4):
    """`count` turns on the spot: quarter=1 right, -1 left, 2 about-face.
    4 right turns should end facing exactly the way it started."""
    m = None
    try:
        m = _setup()
        for _ in range(count):
            m.turn(quarter)
            uct_mouse.delay_ms(300)
        _report(m, "turns(%d x %d)" % (quarter, count))
    finally:
        uct_mouse.set_motors(0, 0)


def pirouette():
    """The 360 deg clockwise target-room spin."""
    m = None
    try:
        m = _setup()
        m.pirouette()
        _report(m, "pirouette")
    finally:
        uct_mouse.set_motors(0, 0)


def sensors(n=10):
    """Put the mouse CENTRED in a dead end (walls left, front and right),
    then run this. Prints the processed and raw ToF readings (L / C / R)."""
    uct_mouse.init()
    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(200)
    raw = getattr(uct_mouse, "get_tof_raw", None)
    print("        get_tof L/C/R        get_tof_raw L/C/R")
    for _ in range(n):
        t = uct_mouse.get_tof()
        line = "  %5d %5d %5d" % (t[0], t[2], t[4])
        if raw is not None:
            r = raw()
            line += "      %5d %5d %5d" % (r[0], r[2], r[4])
        print(line)
        uct_mouse.delay_ms(200)
    print("Calibration (old firmware) read about 100 / 40 / 100 here.")


def clock(seconds=10):
    """Is the mouse's microsecond clock right? Start a phone stopwatch when
    the OLED shows GO and stop it when it shows STOP. Should be `seconds`."""
    import time
    uct_mouse.init()
    for s in (3, 2, 1):
        uct_mouse.display_text(1, "Ready %d..." % s)
        uct_mouse.delay_ms(1000)
    uct_mouse.display_text(1, "GO")
    t0 = time.ticks_us()
    m0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_us(), t0) < seconds * 1000000:
        pass
    uct_mouse.display_text(1, "STOP")
    print("ticks_us says %d s; ticks_ms says %.2f s" % (seconds, time.ticks_diff(time.ticks_ms(), m0) / 1000.0))
    print("What did your stopwatch say?")
