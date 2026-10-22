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


def _report(m, label):
    l, f, r = m.read_walls()
    print("%s done in %.1f s" % (label, m.dt_sum))
    print("  ToF now  L %d  C %d  R %d   (centred: sides ~100, dead-end front ~75)"
          % (m.tof_l, m.tof_c, m.tof_r))
    print("  walls seen  left %s  front %s  right %s" % (l, f, r))
    print("  heading error %+.1f deg   wall heading correction %+.1f deg"
          % (m.target_yaw - m.yaw(), m.yaw_corr))
    print("  odometry scale %.3f   wall-edge fixes %d" % (m.odo_scale, m.edge_fixes))
    if m.turns_done:
        print("  turns: %d, mean error %.1f deg, worst %.1f deg"
              % (m.turns_done, m.turn_err_sum / m.turns_done, m.turn_err_max))


def move(cells=1, v=0.20):
    """Drive `cells` cells straight and stop at the centre."""
    m = None
    try:
        m = _setup()
        m.move(cells, v_max=v, accel=0.8)
        _report(m, "move(%d)" % cells)
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
