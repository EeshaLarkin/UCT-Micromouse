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
import gc
import math
import time
import uct_mouse

ON_HARDWARE = (sys.implementation.name == "micropython")

# ---------------------------------------------------------------------------
# Chassis constants (sim values are derived from tools/simulation_config.json)
# ---------------------------------------------------------------------------
# Which of get_tof()'s 5 slots are the left / centre / right sensors
# (hardware confirmed by calibrate test 1: slots 1 and 3 always read 2000)
TOF_L, TOF_C, TOF_R = 0, 2, 4

if ON_HARDWARE:
    GYRO_SCALE = 1.018        # test 4 in the maze: 1.0179 (misfit 3.7 deg)
    TICKS_PER_M = 6000.0      # test 3 in the maze: 6144 / 5893 / 5979 (mean 6005)
    ODO_SCALE_START = 1.0     # learnt online from wall edges
    DEAD_BAND = 25.0          # calibrate test 2: left 22, right 28 PWM
    V_AT_FULL = 0.41          # test 3 in the maze, real timing: 0.40 / 0.41 / 0.42 m/s
    HALF_AXLE_M = 0.052       # test 4 in the maze: 0.051 / 0.0521; chassis value 0.054
else:
    GYRO_SCALE = 1.0
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
# The real VL53L0X sensors read ~45 mm MORE than the true distance (factory
# offset, not calibrated per sensor). Only differences between readings
# matter for control, so we simply use the measured readings.
# Calibrate test 1 (dead end, centred): left 104, front 75, right 96
#   (left + right = 200 -> consistent; mouse was ~4 mm right of centre)
# Open cell: sides 280-850, front 265 / 440 (walls 1-2 cells further on)
# ---------------------------------------------------------------------------
if ON_HARDWARE:
    SIDE_NOMINAL_MM = 100.0   # side reading when centred  (test 1: 104 / 96)
    FRONT_STOP_MM = 40.0      # front reading when centred. Mouse is 14 cm long in a 19 cm cell
                              # -> ~2.5 cm gap each end. drivetest stopped at ~77 with the nose
                              # ~6-7 cm away = ~3.8 cm short. (test 1's 75 was hand-placed)
    SIDE_WALL_MM = 180.0      # reading below this at a cell centre = wall
    FRONT_WALL_MM = 180.0     #   (walls read 75-104, open reads >= 265)
    SIDE_VALID_MM = 150.0     # use a side wall for centring only if this close
    FRONT_TRUST_MM = 300.0    # front wall close enough to correct the odometry
else:
    SIDE_NOMINAL_MM = 60.0
    FRONT_STOP_MM = 35.0
    SIDE_WALL_MM = 120.0
    FRONT_WALL_MM = 120.0
    SIDE_VALID_MM = 95.0
    FRONT_TRUST_MM = 230.0
SENSOR_AHEAD_MM = 50.0        # side sensors are this far ahead of the centre
EDGE_SNAP_MM = 45.0           # max odometry error a wall edge may correct

# ---------------------------------------------------------------------------
# Controller gains (all in physical units)
# ---------------------------------------------------------------------------
K_HEADING = 7.0     # rad/s of turn per rad of heading error
K_LATERAL = 40.0    # rad/s of turn per metre of offset from corridor centre
K_ALIGN = 1.5       # how fast walls re-align the heading estimate (rad/s per m)
if ON_HARDWARE:
    # Real motors keep rolling below the from-rest deadband, so the mouse
    # didn't slow down when told to (drivetest: ~25 mm overshoot). Stronger
    # speed feedback lets the controller actually brake (negative PWM).
    K_VEL = 150.0       # PWM per (m/s) of wheel-speed error
    STOP_LEAD_M = 0.008 # drivetest 2: still ~10-20 mm past centre -> end 8 mm early
    FRONT_EMERGENCY_MM = FRONT_STOP_MM - 12.0   # past the centre: stop NOW
    # drivetest showed NO slowing before the stop (v_cmd 200 -> 0 in one
    # step) and then a ~30 mm coast. So on the real mouse:
    DECEL = 0.25        # m/s^2 for slowing down: starts ~80 mm before a stop
    FRONT_BLEND = 0.4   # blend in front-ToF fixes gradually (sensor jitter)
    BRAKE_GAIN = 300.0  # active brake: reverse PWM per m/s of wheel speed...
    BRAKE_MAX = 35.0    # ...but never more than this
    STALL_TICKS = 100   # ~1 s at under a third of commanded speed -> give up
    BRAKE_HOLD = 2.0    # PWM per degree of heading error while braking (max 15)
    BRAKE_FF_CUT = 0.04 # m/s too fast -> drop the forward PWM, let feedback brake
else:
    K_VEL = 60.0
    STOP_LEAD_M = 0.0
    FRONT_EMERGENCY_MM = -1.0                  # (not used in the simulator)
    DECEL = None        # simulator: brake at the move's own accel
    FRONT_BLEND = 1.0
    BRAKE_GAIN = 0.0
    BRAKE_MAX = 0.0
    STALL_TICKS = 100000
    BRAKE_HOLD = 0.0
    BRAKE_FF_CUT = None
K_VEL_I = 400.0     # PWM per (m/s * s): integral term, cancels motor imbalance
ACCEL = 1.2         # m/s^2  speed-up / slow-down for straights
V_MIN = 0.05        # m/s    crawl speed at the very end of a move

if ON_HARDWARE:
    # test 4: spinning on the spot at ~200 deg/s needed PWM ~60 (scrubbing
    # friction). Tune on the maze.
    TURN_FAST_PWM = 60
    TURN_SLOW_PWM = 45
else:
    TURN_FAST_PWM = 70
    TURN_SLOW_PWM = 45
TURN_SLOW_ZONE_DEG = 30.0     # switch to slow speed this far from the target
TURN_LEAD_DEG = 3.0           # cut the motors this early (motor lag coasting)

# Real mouse: bang-bang turns coasted ~13 deg past the target (drivetest),
# so turns use a speed profile through the wheel-speed controller instead:
# spin up, slow down smoothly (w = sqrt(2 * alpha * angle left)), then nudge
# to within TURN_DONE_DEG. The simulator keeps the proven bang-bang turns.
PROFILED_TURNS = ON_HARDWARE
TURN_W_MAX = 200.0            # deg/s top spin rate
TURN_ALPHA = 600.0            # deg/s^2 slow-down: starts ~33 deg before the end
TURN_W_MIN = 30.0             # deg/s crawl near the end
TURN_DONE_DEG = 1.5           # finished when this close...
TURN_DONE_RATE = 25.0         # ...and turning slower than this (deg/s)


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
        self.t_last = time.ticks_us() if ON_HARDWARE else 0
        self.dt_sum = 0.0         # hardware: real seconds spent in tick()
        self.dt = DT              # length of the last control period (s)
        self.odo_scale = ODO_SCALE_START  # learnt ground-metres per encoder-metre (slip)
        self.since_fix = 0.0      # ground distance driven since last position fix
        # diagnostics (counters only - lists would grow and eat the STM32's RAM)
        self.edge_fixes = 0       # wall-edge position corrections made
        self.edge_err_sum = 0.0   # total size of those corrections (m)
        self.turns_done = 0
        self.turn_err_sum = 0.0   # heading error left after turns (deg)
        self.turn_err_max = 0.0
        self.arcs_done = 0
        self.v_cmd = 0.0          # forward speed currently commanded (m/s)
        self.log = None           # drivetest sets this to an array to record
        self.emergency_stops = 0
        self.stalls = 0
        self.late = 0.0           # how far past a curve's ideal start we are (m)
        self.rate = 0.0           # gyro turn rate, deg/s (CCW +)

    # ------------------------------------------------------------------
    # The 10 ms heartbeat
    # ------------------------------------------------------------------
    def tick(self, pwm_l=0, pwm_r=0):
        uct_mouse.set_motors(int(pwm_l), int(pwm_r))
        dt = DT
        if ON_HARDWARE:
            # Only wait for whatever is LEFT of the 10 ms period (our own
            # code also takes time), then measure the real period and use it
            # everywhere (gyro, speeds, ramps). With a fixed delay the loop
            # averaged 19.5 ms, and a fixed 0.01 s would have under-counted
            # every turn by ~49%.
            # The simulator runs in lock-step 10 ms steps, so it keeps DT.
            # uct_mouse.delay_ms() overshoots on the real mouse (memcheck:
            # delay_ms(10) took 17.4 ms - background interrupts steal time),
            # so wait by watching the microsecond clock instead.
            period_us = LOOP_MS * 1000
            while time.ticks_diff(time.ticks_us(), self.t_last) < period_us:
                pass
            now = time.ticks_us()
            dt = time.ticks_diff(now, self.t_last) / 1e6
            self.t_last = now
            dt = clamp(dt, 0.005, 0.1)
            self.dt_sum += dt
        else:
            uct_mouse.delay_ms(LOOP_MS)
        self.dt = dt
        self.ticks += 1

        l, r = uct_mouse.get_encoders()
        dl, dr = l - self.lenc, r - self.renc
        self.lenc, self.renc = l, r
        # low-passed wheel speeds (encoder counts are coarse at 10 ms)
        self.v_l += 0.4 * (dl / TICKS_PER_M / dt - self.v_l)
        self.v_r += 0.4 * (dr / TICKS_PER_M / dt - self.v_r)

        self.rate = (uct_mouse.get_gyro() - self.gyro_bias) * GYRO_SCALE   # deg/s
        self.theta += self.rate * dt

        t = uct_mouse.get_tof()
        self.tof_l, self.tof_c, self.tof_r = t[TOF_L], t[TOF_C], t[TOF_R]
        return dl, dr

    def yaw(self):
        """Best estimate of heading relative to the maze grid (deg)."""
        return self.theta + self.yaw_corr

    def stop(self, max_ticks=60):
        """Motors off, then wait until the wheels have actually stopped."""
        self.v_cmd = 0.0
        for _ in range(max_ticks):
            # Real mouse: brake each wheel actively (gentle reverse PWM in
            # proportion to its own speed) - just cutting the power let it
            # coast ~30 mm, and the two wheels coasted differently (= a turn).
            pl = pr = 0
            if BRAKE_GAIN > 0.0:
                # brake against whichever way each wheel is rolling (during
                # a turn one wheel runs backwards)
                if abs(self.v_l) > 0.02:
                    pl = -clamp(BRAKE_GAIN * self.v_l, -BRAKE_MAX, BRAKE_MAX)
                if abs(self.v_r) > 0.02:
                    pr = -clamp(BRAKE_GAIN * self.v_r, -BRAKE_MAX, BRAKE_MAX)
                if pl or pr:
                    # hold the heading while braking: the motors aren't equally
                    # strong, so equal braking twisted the mouse 3-5 deg
                    h = clamp(BRAKE_HOLD * wrap180(self.target_yaw - self.yaw()), -15.0, 15.0)
                    pl -= h
                    pr += h
            self.tick(pl, pr)
            if self.log is not None and len(self.log) < 1500:
                self.log.extend((0, int((self.v_l + self.v_r) * 500),
                                 int(min(self.tof_c, 9999)), int(pl), int(pr)))
            if abs(self.v_l) < 0.005 and abs(self.v_r) < 0.005:
                break
        uct_mouse.set_motors(0, 0)
        if ON_HARDWARE:
            # Every float calculation leaves a little garbage; MicroPython
            # pauses to clean it up when memory fills. Clean up now, while
            # standing still, rather than in the middle of the next move.
            gc.collect()
            self.t_last = time.ticks_us()     # don't count the cleanup as a tick

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
        if ON_HARDWARE:
            self.t_last = time.ticks_us()

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
    def _pwm_for(self, v_cmd, v_meas, integ, sat=True):
        """Feed-forward (deadband + linear motor model) plus PI speed feedback.

        Feed-forward gets us close instantly; P reacts to disturbances; the
        integral slowly finds the extra PWM a weak motor needs, so the steering
        loop doesn't have to hold a permanent heading error to compensate.
        Returns (pwm, updated integrator)."""
        if abs(v_cmd) < 1e-4:
            return 0, integ
        err = v_cmd - v_meas
        integ = clamp(integ + K_VEL_I * err * self.dt, -25.0, 25.0)
        ff = DEAD_BAND + abs(v_cmd) / V_AT_FULL * (100.0 - DEAD_BAND)
        if BRAKE_FF_CUT is not None and (err * v_cmd) < 0 and abs(err) > BRAKE_FF_CUT:
            # Real mouse: drivetest showed v_real ~170 when asked for ~70,
            # because the feed-forward kept ~35 PWM pushing forward. When a
            # wheel is clearly too fast (either direction), drop it and let
            # the feedback term brake.
            ff = 0.0
        pwm = (ff if v_cmd > 0 else -ff) + K_VEL * err + integ
        return (clamp(pwm, -100, 100) if sat else pwm), integ

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
        """Drive `cells` cells straight along target_yaw and stop at the centre."""
        self._drive(0.0, cells * CELL_M, cells * CELL_M, v_max, 0.0, accel, use_front)

    def _drive(self, s, s_end, s_cell, v_max, v_end, accel, use_front=True):
        """Drive straight along target_yaw from s to s_end (metres, measured
        from the centre of the cell this straight started in). s_cell is the
        centre of the last cell of the straight. Arrive at speed v_end:
        0 = stop there, >0 = hand over to a curved turn without stopping.

        Speed profile: v = min(v_max, accelerate-from-v_prev, sqrt(v_end^2 + 2*a*remaining))
          - the last term is v^2 = v_end^2 + 2*a*d: the fastest speed from
            which we can still brake to v_end in the remaining distance.
        Steering (omega = turn rate):
          omega = K_HEADING * heading_error - K_LATERAL * offset_from_centre
          - gyro keeps us pointing along the corridor,
          - side walls pull us back to the centre line,
          - K_ALIGN slowly corrects the heading estimate so the gyro and the
            walls agree (removes drift and the hidden yaw slip after turns).
        Front wall: if a wall is visible just ahead near the end, its distance
        replaces the encoder estimate (absolute position fix).
        Wall edges ('posts'): walls only start/end on cell boundaries, which
        lie 100, 300, 500... mm from the starting cell centre. A side sensor is
        50 mm ahead of the centre, so when a side reading jumps between 'wall'
        and 'open' the robot's centre must be at 50, 250, 450... mm. Snapping
        s to that value removes the slip that the encoders can't see.
        """
        if s_end - s < 0.001:
            # Zero-length straight (two curves back to back). Check the wall
            # ahead first: if we left the last curve early, drive the gap so
            # the next curve doesn't start early and cut the inner corner.
            self.late = 0.0
            if not (use_front and self.tof_c < FRONT_TRUST_MM):
                return
            s_tof = s_cell - (self.tof_c - FRONT_STOP_MM) / 1000.0
            if abs(s_tof - s) > 0.08:
                return
            if s_end - s_tof < 0.003:
                self.late = s_tof - s_end      # past the ideal start: tighten
                return
            s = s_tof
            self.since_fix = 0.0
        v = self.v_cmd
        decel = accel if DECEL is None else min(accel, DECEL)
        stall = 0
        y_f = None                    # filtered lateral offset
        prev_l = self.tof_l < SIDE_VALID_MM
        prev_r = self.tof_r < SIDE_VALID_MM
        front_fix = False
        for _ in range(int(20 * (s_end - s) / 0.2 / max(v_max, 0.05)) + 300):
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
                                               0.85, 1.15)
                    self.since_fix = 0.0
                    self.edge_fixes += 1
                    self.edge_err_sum += abs(s_edge - s)
                    s = s_edge
            prev_l, prev_r = now_l, now_r

            # front wall of the last cell -> exact distance to its centre
            if use_front and self.tof_c < FRONT_TRUST_MM and s_cell - s < 0.25:
                s_tof = s_cell - (self.tof_c - FRONT_STOP_MM) / 1000.0
                if abs(s_tof - s) < 0.08:
                    s += FRONT_BLEND * (s_tof - s)
                    front_fix = True
                    # This is a position fix too: restart the slip learner
                    # from here, or the jump would be mistaken for slip.
                    self.since_fix = 0.0
            rem = s_end - s
            if self.tof_c < FRONT_EMERGENCY_MM:
                self.emergency_stops += 1          # too close to a wall: stop
                break
            if rem <= 0.002 + (STOP_LEAD_M if v_end <= 0.0 else 0.0):
                break

            v = min(v_max, v + accel * self.dt,
                    math.sqrt(v_end * v_end + 2.0 * decel * max(rem, 0.0)))
            v = max(v, V_MIN)

            # stall: wheels far slower than commanded for ~1 s (stuck cable,
            # pushing a wall) -> stop instead of cooking the motors
            if v > 0.1 and (self.v_l + self.v_r) < 0.66 * v:
                stall += 1
                if stall > STALL_TICKS:
                    self.stalls += 1
                    break
            else:
                stall = 0

            yaw_err = math.radians(wrap180(self.target_yaw - self.yaw()))
            omega = K_HEADING * yaw_err
            y = self._lateral_offset()
            if y is None:
                y_f = None
            else:
                y_f = y if y_f is None else y_f + 0.3 * (y - y_f)
                omega -= K_LATERAL * y_f
                self.yaw_corr += math.degrees(K_ALIGN * y_f * self.dt)

            ds = self._wheels(v, omega)
            s += ds
            self.since_fix += ds
        self.v_cmd = v
        self.late = max(0.0, s - s_end)        # how far past the handover point
        if v_end <= 0.0:
            self.stop()
            if front_fix:
                self.since_fix = 0.0  # we stopped at a measured distance from a wall

    def _wheels(self, v, omega):
        """One tick of wheel-speed control for forward speed v (m/s) and turn
        rate omega (rad/s). Returns the distance travelled (m)."""
        vl_cmd = v - omega * HALF_AXLE_M
        vr_cmd = v + omega * HALF_AXLE_M
        pl, self.i_l = self._pwm_for(vl_cmd, self.v_l, self.i_l, sat=False)
        pr, self.i_r = self._pwm_for(vr_cmd, self.v_r, self.i_r, sat=False)
        # Desaturation: if a wheel would need >100% PWM (weak motor, flat
        # battery, top speed), lower BOTH wheels by the excess. Their
        # difference - the steering - is kept exactly; only speed is lost.
        excess = max(pl, pr) - 100.0
        if excess > 0:
            pl -= excess
            pr -= excess
        pl = clamp(pl, -100, 100)
        pr = clamp(pr, -100, 100)
        dl, dr = self.tick(pl, pr)
        if self.log is not None and len(self.log) < 1500:
            # recorder for drivetest: commanded vs measured speed (mm/s),
            # front ToF (mm) and the PWMs actually sent - 5 numbers per tick
            self.log.extend((int(v * 1000), int((self.v_l + self.v_r) * 500),
                             int(min(self.tof_c, 9999)), int(pl), int(pr)))
        return (dl + dr) / 2.0 / TICKS_PER_M * self.odo_scale

    # ------------------------------------------------------------------
    # Curved ("smooth") turns for the sprint
    # ------------------------------------------------------------------
    def arc(self, quarter, v):
        """Sweep a 90 deg corner without stopping: a quarter circle of radius
        R = half a cell around the inner corner post, from the boundary where
        we enter the corner cell to the boundary where we leave it.

        Physics: on a circle omega = v / R. The heading we SHOULD have is
        start + (distance along arc) / R, so the gyro loop only corrects small
        errors on top of that feed-forward. Path length = (pi/2) * R = 157 mm.
        Wheel speeds: v * (1 -/+ HALF_AXLE/R) -> the outer wheel runs ~1.5x v,
        which is why v must be lower here than on straights.
        """
        # Started late by d? A radius of (R - d) still exits on the centre
        # line of the new corridor (late distance + radius = same 100 mm),
        # instead of swinging d mm closer to the outer wall.
        R = CELL_M / 2.0 - clamp(self.late, 0.0, 0.04)
        self.late = 0.0
        sign = -1.0 if quarter > 0 else 1.0        # right = clockwise = -
        yaw0 = self.target_yaw
        length = math.pi / 2.0 * R
        s = 0.0
        for _ in range(int(length / max(v, 0.05) / DT) + 100):
            if s >= length:
                break
            ref = yaw0 + sign * math.degrees(s / R)
            omega = sign * v / R + K_HEADING * math.radians(wrap180(ref - self.yaw()))
            s += self._wheels(v, omega)
        self.target_yaw = yaw0 + sign * 90.0
        self.v_cmd = v
        self.arcs_done += 1

    def sweep_path(self, segments, v_max, v_turn, accel):
        """Drive a whole compressed path without stopping at corners.

        segments: [(n_cells, quarter_turn_INTO_this_segment), ...]
        Every straight is measured from the centre of its first cell: it
        starts 100 mm in (we leave the previous arc at the cell boundary) and
        ends 100 mm before the centre of its last cell (where the next arc
        begins). The last straight ends at the cell centre and stops.
        """
        last = len(segments) - 1
        for i in range(len(segments)):
            n, q = segments[i]
            if i == 0:
                if q != 0:
                    self.turn(q)                    # first heading: on the spot
                s0 = 0.0
            elif q in (1, -1):
                self.arc(q, v_turn)
                s0 = CELL_M / 2.0
            else:                                    # U-turn (BFS paths never need one)
                self.stop()
                self.turn(q)
                s0 = 0.0
            if i == last:
                self._drive(s0, n * CELL_M, n * CELL_M, v_max, 0.0, accel)
            else:
                self._drive(s0, n * CELL_M - CELL_M / 2.0, n * CELL_M, v_max, v_turn, accel)

    # ------------------------------------------------------------------
    # Turning on the spot (two-speed bang-bang on gyro angle)
    # ------------------------------------------------------------------
    def _rotate_profiled(self, yaw_target, timeout_ticks=500):
        """Turn on the spot to yaw_target with a planned spin rate:
        w = min(W_MAX, accelerate, sqrt(2 * alpha * angle_left)), sent to the
        wheel-speed controller as omega (which brakes actively if needed).
        Near the end it crawls at W_MIN and may nudge back if it overshot."""
        w = 0.0
        settled = 0
        for _ in range(timeout_ticks):
            err = yaw_target - self.yaw()       # deg (can be up to 360 for the pirouette)
            a = abs(err)
            if a < TURN_DONE_DEG and abs(self.rate) < TURN_DONE_RATE:
                settled += 1
                if settled >= 3:
                    break
            else:
                settled = 0
            w_mag = min(TURN_W_MAX, abs(w) + TURN_ALPHA * 2.0 * self.dt,
                        math.sqrt(2.0 * TURN_ALPHA * a))
            w_mag = max(w_mag, TURN_W_MIN) if a > TURN_DONE_DEG else 0.0
            w = w_mag if err > 0 else -w_mag
            self._wheels(0.0, math.radians(w))
        self.stop()

    def _rotate_to(self, yaw_target, fast_pwm=TURN_FAST_PWM, timeout_ticks=400):
        if PROFILED_TURNS:
            self._rotate_profiled(yaw_target, timeout_ticks + 100)
            if yaw_target == self.target_yaw:
                e = abs(self.target_yaw - self.yaw())
                self.turns_done += 1
                self.turn_err_sum += e
                self.turn_err_max = max(self.turn_err_max, e)
            return
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
