# =========================================================================
# motion.py  -  The "legs and eyes" of the Micromouse
# =========================================================================
# Everything that touches uct_mouse lives here. maze_logic.py decides WHERE
# to go; this file makes the robot physically get there.
#
# One control period ("tick") = 10 ms: set motors -> wait 10 ms -> read
# encoders, gyro and ToFs -> update the state estimate. Every loop below is
# built from ticks, so the gyro is integrated continuously, even while
# stopped or sensing walls.
#
# Angles: degrees, CCW positive (matches the gyro). A RIGHT turn is negative.
# =========================================================================

import sys
import math
import uct_mouse

ON_HARDWARE = (sys.implementation.name == "micropython")

# ---------------------------------------------------------------------------
# Chassis constants (sim values are derived from tools/simulation_config.json)
# ---------------------------------------------------------------------------
if ON_HARDWARE:
    TICKS_PER_M = 5730.0      # 1170 ticks/rev / (2*pi*0.0325 m wheel radius)
    ODO_SCALE_START = 1.0     # learnt online from wall edges
    DEAD_BAND = 58.0          # PWM below which the wheels don't move (measured)
    V_AT_FULL = 0.40          # m/s at PWM 100  -> MEASURE ON HARDWARE
    HALF_AXLE_M = 0.045       # half the wheel spacing -> MEASURE ON HARDWARE
else:
    TICKS_PER_M = 4400.0      # 470 ticks/rev / (2*pi*0.017 m wheel radius)
    ODO_SCALE_START = 0.96    # sim wheel slip makes encoders over-read ~4%
    DEAD_BAND = 28.0
    V_AT_FULL = 0.40          # simulator max_speed
    HALF_AXLE_M = 0.054

LOOP_MS = 10
DT = 0.01                     # keep fixed: the simulator steps in 10 ms
CELL_M = 0.20

# ---------------------------------------------------------------------------
# Wall geometry (mm). Side ToFs sit 40 mm either side of centre and 50 mm
# ahead of it; the front ToF is 65 mm ahead. In a centred cell:
#   side wall  = 100 - 40 = 60 mm   (sim: walls are zero-thickness lines)
#   front wall = 100 - 65 = 35 mm
# Real walls have thickness, so the hardware numbers are smaller -> MEASURE.
# ---------------------------------------------------------------------------
if ON_HARDWARE:
    SIDE_NOMINAL_MM = 57.0    # MEASURE: side reading when centred
    FRONT_STOP_MM = 32.0      # MEASURE: front reading when centred
else:
    SIDE_NOMINAL_MM = 60.0
    FRONT_STOP_MM = 35.0
SIDE_WALL_MM = 120.0          # reading below this at a cell centre = wall
FRONT_WALL_MM = 120.0
SIDE_VALID_MM = 95.0          # use a side wall for centring only if this close
FRONT_TRUST_MM = 230.0        # front wall close enough to correct the odometry
SENSOR_AHEAD_MM = 50.0        # side sensors are this far ahead of the centre
EDGE_SNAP_MM = 45.0           # max odometry error a wall edge may correct

# ---------------------------------------------------------------------------
# Controller gains (all in physical units)
# ---------------------------------------------------------------------------
K_HEADING = 7.0     # rad/s of turn per rad of heading error
K_LATERAL = 40.0    # rad/s of turn per metre of offset from corridor centre
K_ALIGN = 1.5       # how fast walls re-align the heading estimate (rad/s per m)
K_VEL = 60.0        # PWM per (m/s) of wheel-speed error
K_VEL_I = 400.0     # PWM per (m/s * s): integral term, cancels motor imbalance
ACCEL = 1.2         # m/s^2  speed-up / slow-down for straights
V_MIN = 0.05        # m/s    crawl speed at the very end of a move

TURN_FAST_PWM = 70
TURN_SLOW_PWM = 45
TURN_SLOW_ZONE_DEG = 30.0     # switch to slow speed this far from the target
TURN_LEAD_DEG = 3.0           # cut the motors this early (motor lag coasting)


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def wrap180(a):
    while a > 180.0:
        a -= 360.0
    while a < -180.0:
        a += 360.0
    return a


class Motion:
    def __init__(self):
        self.gyro_bias = 0.0
        self.theta = 0.0          # integrated gyro yaw (deg)
        self.yaw_corr = 0.0       # wall-based correction added to theta (deg)
        self.target_yaw = 0.0     # the maze direction we SHOULD be facing (deg)
        self.lenc, self.renc = uct_mouse.get_encoders()
        self.v_l = 0.0            # measured wheel speeds (m/s)
        self.v_r = 0.0
        self.i_l = 0.0            # wheel-speed integrators (PWM)
        self.i_r = 0.0
        self.tof_l = self.tof_c = self.tof_r = 8190.0
        self.ticks = 0            # time in control periods
        self.odo_scale = ODO_SCALE_START  # learnt ground-metres per encoder-metre (slip)
        self.since_fix = 0.0      # ground distance driven since last position fix
        # diagnostics (counters only - lists would grow and eat the STM32's RAM)
        self.edge_fixes = 0       # wall-edge position corrections made
        self.edge_err_sum = 0.0   # total size of those corrections (m)
        self.turns_done = 0
        self.turn_err_sum = 0.0   # heading error left after turns (deg)
        self.turn_err_max = 0.0

    # ------------------------------------------------------------------
    # The 10 ms heartbeat
    # ------------------------------------------------------------------
    def tick(self, pwm_l=0, pwm_r=0):
        uct_mouse.set_motors(int(pwm_l), int(pwm_r))
        uct_mouse.delay_ms(LOOP_MS)
        self.ticks += 1

        l, r = uct_mouse.get_encoders()
        dl, dr = l - self.lenc, r - self.renc
        self.lenc, self.renc = l, r
        # low-passed wheel speeds (encoder counts are coarse at 10 ms)
        self.v_l += 0.4 * (dl / TICKS_PER_M / DT - self.v_l)
        self.v_r += 0.4 * (dr / TICKS_PER_M / DT - self.v_r)

        self.theta += (uct_mouse.get_gyro() - self.gyro_bias) * DT

        t = uct_mouse.get_tof()
        self.tof_l, self.tof_c, self.tof_r = t[0], t[2], t[4]
        return dl, dr

    def yaw(self):
        """Best estimate of heading relative to the maze grid (deg)."""
        return self.theta + self.yaw_corr

    def stop(self, max_ticks=60):
        """Motors off, then wait until the wheels have actually stopped."""
        for _ in range(max_ticks):
            self.tick(0, 0)
            if abs(self.v_l) < 0.005 and abs(self.v_r) < 0.005:
                break

    # ------------------------------------------------------------------
    # Start-up
    # ------------------------------------------------------------------
    def calibrate_gyro(self, samples=100):
        """Average the gyro while standing still: that average is the bias."""
        for _ in range(20):
            self.tick(0, 0)
        total = 0.0
        for _ in range(samples):
            uct_mouse.delay_ms(LOOP_MS)
            total += uct_mouse.get_gyro()
        self.gyro_bias = total / samples
        self.theta = 0.0
        self.lenc, self.renc = uct_mouse.get_encoders()

    # ------------------------------------------------------------------
    # Wall sensing (call while stopped at a cell centre)
    # ------------------------------------------------------------------
    def read_walls(self, samples=5):
        """Average a few readings and classify (left, front, right) walls."""
        sl = sc = sr = 0.0
        for _ in range(samples):
            self.tick(0, 0)
            sl += min(self.tof_l, 500)
            sc += min(self.tof_c, 500)
            sr += min(self.tof_r, 500)
        sl /= samples
        sc /= samples
        sr /= samples
        return sl < SIDE_WALL_MM, sc < FRONT_WALL_MM, sr < SIDE_WALL_MM

    # ------------------------------------------------------------------
    # Pure wheel-speed control
    # ------------------------------------------------------------------
    def _pwm_for(self, v_cmd, v_meas, integ):
        """Feed-forward (deadband + linear motor model) plus PI speed feedback.

        Feed-forward gets us close instantly; P reacts to disturbances; the
        integral slowly finds the extra PWM a weak motor needs, so the steering
        loop doesn't have to hold a permanent heading error to compensate.
        Returns (pwm, updated integrator)."""
        if abs(v_cmd) < 1e-4:
            return 0, integ
        err = v_cmd - v_meas
        integ = clamp(integ + K_VEL_I * err * DT, -25.0, 25.0)
        ff = DEAD_BAND + abs(v_cmd) / V_AT_FULL * (100.0 - DEAD_BAND)
        pwm = (ff if v_cmd > 0 else -ff) + K_VEL * err + integ
        return clamp(pwm, -100, 100), integ

    def _lateral_offset(self):
        """Offset from the corridor centre-line in metres (+ = left of centre),
        or None when there's no side wall close enough to measure from."""
        lv = self.tof_l < SIDE_VALID_MM
        rv = self.tof_r < SIDE_VALID_MM
        if lv and rv:
            return (self.tof_r - self.tof_l) / 2000.0
        if lv:
            return (SIDE_NOMINAL_MM - self.tof_l) / 1000.0
        if rv:
            return (self.tof_r - SIDE_NOMINAL_MM) / 1000.0
        return None

    # ------------------------------------------------------------------
    # Straight moves
    # ------------------------------------------------------------------
    def move(self, cells, v_max=0.25, accel=ACCEL, use_front=True):
        """Drive `cells` cells straight along target_yaw and stop at the centre.

        Speed profile: v = min(v_max, accelerate-from-v_prev, sqrt(2*a*remaining))
          - the last term is v^2 = 2*a*d: the fastest speed from which we
            can still brake to zero in the remaining distance.
        Steering (omega = turn rate):
          omega = K_HEADING * heading_error - K_LATERAL * offset_from_centre
          - gyro keeps us pointing along the corridor,
          - side walls pull us back to the centre line,
          - K_ALIGN slowly corrects the heading estimate so the gyro and the
            walls agree (removes drift and the hidden yaw slip after turns).
        Front wall: if a wall is visible just ahead near the end of the move,
        its distance replaces the encoder estimate (absolute position fix).
        Wall edges ('posts'): walls only start/end on cell boundaries, which
        lie 100, 300, 500... mm from where we started. A side sensor is 50 mm
        ahead of the centre, so when a side reading jumps between 'wall' and
        'open' the robot's centre must be at 50, 250, 450... mm. Snapping s to
        that value removes the slip that the encoders can't see.
        """
        dist = cells * CELL_M
        s = 0.0
        v = 0.0
        y_f = None                    # filtered lateral offset
        prev_l = self.tof_l < SIDE_VALID_MM
        prev_r = self.tof_r < SIDE_VALID_MM
        front_fix = False
        for _ in range(int(20 * cells / max(v_max, 0.05)) + 300):
            now_l = self.tof_l < SIDE_VALID_MM
            now_r = self.tof_r < SIDE_VALID_MM
            if now_l != prev_l or now_r != prev_r:
                half = CELL_M * 500.0                             # 100 mm
                k = round((s * 1000.0 - (half - SENSOR_AHEAD_MM)) / (2 * half))
                s_edge = (k * 2 * half + half - SENSOR_AHEAD_MM) / 1000.0
                if abs(s_edge - s) < EDGE_SNAP_MM / 1000.0:
                    # The error built up over `since_fix` metres tells us how
                    # much the encoders over/under-read: learn that ratio.
                    if self.since_fix > 0.08:
                        ratio = 1.0 + (s_edge - s) / self.since_fix
                        self.odo_scale = clamp(self.odo_scale * (1.0 + 0.5 * (ratio - 1.0)),
                                               0.85, 1.05)
                    self.since_fix = 0.0
                    self.edge_fixes += 1
                    self.edge_err_sum += abs(s_edge - s)
                    s = s_edge
            prev_l, prev_r = now_l, now_r

            rem = dist - s
            if use_front and self.tof_c < FRONT_TRUST_MM and rem < 0.25:
                rem_tof = (self.tof_c - FRONT_STOP_MM) / 1000.0
                if abs(rem_tof - rem) < 0.08:
                    rem = rem_tof
                    dist = s + rem
                    front_fix = True
            if rem <= 0.002:
                break

            v = min(v_max, v + accel * DT, math.sqrt(2.0 * accel * max(rem, 0.0)))
            v = max(v, V_MIN)

            yaw_err = math.radians(wrap180(self.target_yaw - self.yaw()))
            omega = K_HEADING * yaw_err
            y = self._lateral_offset()
            if y is None:
                y_f = None
            else:
                y_f = y if y_f is None else y_f + 0.3 * (y - y_f)
                omega -= K_LATERAL * y_f
                self.yaw_corr += math.degrees(K_ALIGN * y_f * DT)

            vl_cmd = v - omega * HALF_AXLE_M
            vr_cmd = v + omega * HALF_AXLE_M
            pl, self.i_l = self._pwm_for(vl_cmd, self.v_l, self.i_l)
            pr, self.i_r = self._pwm_for(vr_cmd, self.v_r, self.i_r)
            dl, dr = self.tick(pl, pr)
            ds = (dl + dr) / 2.0 / TICKS_PER_M * self.odo_scale
            s += ds
            self.since_fix += ds
        self.stop()
        if front_fix:
            self.since_fix = 0.0      # we stopped at a measured distance from a wall

    # ------------------------------------------------------------------
    # Turning on the spot (two-speed bang-bang on gyro angle)
    # ------------------------------------------------------------------
    def _rotate_to(self, yaw_target, fast_pwm=TURN_FAST_PWM, timeout_ticks=400):
        for _ in range(timeout_ticks):
            err = yaw_target - self.yaw()
            if abs(err) < TURN_LEAD_DEG:
                break
            pwm = fast_pwm if abs(err) > TURN_SLOW_ZONE_DEG else TURN_SLOW_PWM
            if err > 0:               # need to go CCW (left)
                self.tick(-pwm, pwm)
            else:                     # CW (right)
                self.tick(pwm, -pwm)
        self.stop()
        if yaw_target == self.target_yaw:
            e = abs(self.target_yaw - self.yaw())
            self.turns_done += 1
            self.turn_err_sum += e
            self.turn_err_max = max(self.turn_err_max, e)

    def turn(self, quarter_turns, fast_pwm=TURN_FAST_PWM):
        """+1 = 90 deg right, -1 = 90 deg left, 2 = about-face."""
        if quarter_turns == 0:
            return
        self.target_yaw -= 90.0 * quarter_turns
        self._rotate_to(self.target_yaw, fast_pwm)

    def pirouette(self):
        """Full 360 deg clockwise spin, ending facing the same way."""
        self._rotate_to(self.target_yaw - 360.0, timeout_ticks=800)
        self.theta += 360.0           # same physical direction as before
