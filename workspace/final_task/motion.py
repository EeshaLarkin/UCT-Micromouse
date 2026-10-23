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
# If drivetest.sensors() shows the LEFT wall in the R column on the current
# firmware, set this to True (left and right slots swapped).
SWAP_SIDE_TOFS = False
if SWAP_SIDE_TOFS:
    TOF_L, TOF_R = TOF_R, TOF_L

if ON_HARDWARE:
    GYRO_SCALE = 1.018        # test 4 in the maze: 1.0179 (misfit 3.7 deg)
    # Ticks per metre of ONE wheel. Original firmware, test 3: ~6000.
    # 23 Oct: the LEFT encoder reads 0 (drivetest.wheels(): left 0, right
    # 974 / 933), so test 3's both-wheel average halved: 3121 / 3019 / 3198 /
    # 3199 -> the right wheel alone ~6270.
    # Right wheel only (left encoder dead). drivetest.distance_check(2),
    # encoders only, 23 Oct: 6211 / 6135 / 5970 (mean 6105). Agrees with the
    # 16:57 maze run, whose moves were ~10% short at 5500.
    TICKS_PER_M = 6100.0
    # ...but the mission log (23 Oct, 15:40) showed each "1 cell" move was
    # really ~235 mm (front 594 -> 359), and move(2)'s front readings agree
    # (~17% further than the encoder said). Test 3 assumed its start distance
    # from geometry, which can't see that. 5500 sits between the two; the
    # odometry learner (wall edges + front walls) fine-tunes it in the maze.
    ODO_SCALE_START = 1.0     # learnt online from wall edges
    DEAD_BAND = 25.0          # calibrate test 2: left 22, right 28 PWM
    V_AT_FULL = 0.45          # 23 Oct test 3: 0.49 / 0.50 (0.165 m/s at PWM 50), but
                              # move(2) topped out lower - 0.45 is a safe middle
    HALF_AXLE_M = 0.052       # test 4 in the maze: 0.051 / 0.0521; chassis value 0.054
else:
    GYRO_SCALE = 1.0
    TICKS_PER_M = 4400.0      # 470 ticks/rev / (2*pi*0.017 m wheel radius)
    ODO_SCALE_START = 0.96    # sim wheel slip makes encoders over-read ~4%
    DEAD_BAND = 28.0
    V_AT_FULL = 0.40          # simulator max_speed
    HALF_AXLE_M = 0.054

# Right-wheel ticks per left-wheel tick over the same distance (calibrate
# test 3 prints it). 1.0 = both encoders count alike.
ENC_RATIO_R_L = 1.0
# Dead left encoder: until the left encoder has counted anything, its
# movement is CALCULATED from the right wheel and the gyro - the difference
# between the wheel speeds is exactly what turns the mouse:
#     v_left = v_right - turn_rate * (2 * half_axle)
# As soon as the left encoder counts (cable fixed), it is used again.
LEFT_FROM_GYRO = ON_HARDWARE
TICKS_L = TICKS_PER_M * 2.0 / (1.0 + ENC_RATIO_R_L)
TICKS_R = TICKS_PER_M * 2.0 * ENC_RATIO_R_L / (1.0 + ENC_RATIO_R_L)

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
    # Side reading when centred. Original firmware: 100 (test 1: 104 / 96).
    # 23 Oct firmware, drivetest.sensors() in a dead end: 70 / 68. (Also
    # re-learnt in the maze; drivetest.move() never learnt it, so it steered
    # off-centre whenever only one side wall was visible.)
    SIDE_NOMINAL_MM = 66.0    # full-maze run: walls read 50-79 when stopped
    # Front reading when centred (nose ~2.5 cm from the wall). The 40 we used
    # left the nose ~1 cm away (photo of the move(1) stop: front 41), and
    # the mission stops at ~50 were "too far forward". Under ~5 cm this
    # sensor is unreliable (55 with the nose almost touching), so the front
    # fix only uses readings above FRONT_STOP_MM + FRONT_FIX_MIN_MM; the last
    # couple of cm are done on the encoder.
    FRONT_STOP_MM = 52.0
    # Full-maze run 23 Oct: an OPENING beside a cell with a front wall can
    # read as little as 133-150 (the side sensor sees the next wall at an
    # angle), and the old limit (149) turned the target room's doorway at
    # (5,0) into a wall (R 133). Walls never read more than ~80.
    SIDE_WALL_MM = 106.0      # reading below this at a cell centre = wall (nominal + 40)
    FRONT_WALL_MM = 180.0     #   (walls read 75-104, open reads >= 265)
    SIDE_VALID_MM = 98.0      # use a side wall for centring only if this close (nominal + 32)
    # Front wall close enough to correct the position. The front sensor reads
    # ~25 mm LONG at 250-300 mm (a centred mouse one cell from a wall reads
    # 277-284, not ~252), so only use it from 200 mm in.
    FRONT_TRUST_MM = 200.0
else:
    SIDE_NOMINAL_MM = 60.0
    FRONT_STOP_MM = 35.0
    SIDE_WALL_MM = 120.0
    FRONT_WALL_MM = 120.0
    SIDE_VALID_MM = 95.0
    FRONT_TRUST_MM = 230.0
SENSOR_AHEAD_MM = 50.0        # side sensors are this far ahead of the centre
# Max odometry error a wall edge may correct. OFF on the real mouse: its
# side sensors see a wall's end earlier than this model assumes, so each
# "fix" pulled the position back, it learnt a too-small distance scale (0.75)
# and overshot a 3-cell move by ~11 cm into a post (full-maze run 23 Oct).
EDGE_SNAP_MM = 0.0 if ON_HARDWARE else 45.0
FRONT_FIX_MIN_MM = 18.0 if ON_HARDWARE else -100.0
# How far the front wall may disagree with the encoders and still be used.
# Readings under 200 mm in the last cell can only be that cell's own front
# wall, so on the real mouse a big disagreement is still trusted: at (5,3)
# it stopped 12 cm short of a wall because 0.08 m rejected the fix.
FRONT_FIX_GATE = 0.15 if ON_HARDWARE else 0.08
# Learning the distance scale from front walls: OFF on the real mouse. The
# sensor's long-range bias taught it a too-small scale, so moves through
# open cells (no wall ahead to stop against) overshot (23 Oct).
FRONT_LEARN = not ON_HARDWARE
# Too close to a front wall after a stop (reading between these): reverse
# gently until the reading is back near FRONT_STOP_MM.
BACKOFF_BELOW_MM = (FRONT_STOP_MM - 8.0) if ON_HARDWARE else -1.0
BACKOFF_ABOVE_MM = 28.0       # below this the reading can't be trusted at all

ODO_SCALE_MIN = 0.75          # learnt odometry scale limits
ODO_SCALE_MAX = 1.25

# --- Robustness (added after the first untethered runs) ---------------------
# Mission log, run 2: a side ToF 29-49 mm from a wall kept dropping out to
# 8190 for a moment. Each blip looked like a wall EDGE, the edge snap pulled
# the position estimate back to 50 mm again and again, so a 1-cell move drove
# ~4 cells. Also 5-sample AVERAGES with a blip read a real wall as open.
DROPOUT_MM = 2000.0           # a reading this big = no echo (8190) / no sensor (2000)
DROPOUT_HOLD = 8 if ON_HARDWARE else 0   # ticks a close reading is kept through a dropout
# The current course firmware reports anything closer than 20 mm as 8190
# (VL53L0X.c: "distance > 20"), and the front reads only ~25-45 mm when the
# mouse is centred against a wall. So a front 8190 straight after a close
# reading means TOO CLOSE, not open: keep the close value until a real one.
FRONT_CLOSE_HOLD_MM = 80.0 if ON_HARDWARE else -1.0
# The current firmware's side readings jump +-40 mm with the mouse standing
# still, so on the real mouse the centring uses a slower filter and ignores
# single readings that disagree wildly with it.
LAT_FILTER = 0.3             # (0.12 suited the noisy Oct firmware)
LAT_OUTLIER_M = 0.05 if ON_HARDWARE else 1.0
WALL_SAMPLES = 15 if ON_HARDWARE else 7  # read_walls: ticks to sample (sensors update every ~30 ms)
EDGE_CONFIRM = 5 if ON_HARDWARE else 1   # a wall edge must last this many ticks to count
OVERRUN = 1.15                # stop if the encoders say we drove 15% + ...
OVERRUN_M = 0.05              # ... 5 cm further than planned (safety net)
YAW_CORR_MAX = 6.0            # walls may re-align the heading by at most this per move (deg)
# Bump recovery (self-correction): a knock against a wall shows up as a big
# sudden heading error (log: +66 deg) or the wheels stalling. Then: stop,
# reverse a few cm straight out, turn back to the corridor heading, carry on.
BUMP_DEG = 20.0 if ON_HARDWARE else None
BUMP_STALL_TICKS = 30         # ~0.3 s of wheels much slower than commanded
# Pressed against a side wall/post: the wheels just slip, so neither the
# heading nor the wheel speeds show it (move(2), 23 Oct: R read 22 while it
# kept pushing). A side reading this low for 5 ticks also counts as a bump.
SIDE_TOUCH_MM = 28.0 if ON_HARDWARE else -1.0
MAX_UNSTICKS = 3              # per move; after that give up on the move
BACKUP_M = 0.03
BACKUP_V = 0.08

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
    # 23 Oct firmware: centred reads ~38 but touching the wall reads ~29, so
    # the old 28 never fired (move(2) pushed the wall at 29 for 0.7 s)
    FRONT_EMERGENCY_MM = 36.0   # nose ~1 cm from the wall: stop NOW
    # drivetest showed NO slowing before the stop (v_cmd 200 -> 0 in one
    # step) and then a ~30 mm coast. So on the real mouse:
    DECEL = 0.25        # m/s^2 for slowing down: starts ~80 mm before a stop
    FRONT_BLEND = 0.4   # blend in front-ToF fixes gradually (sensor jitter)
    BRAKE_GAIN = 300.0  # active brake: reverse PWM per m/s of wheel speed...
    BRAKE_MAX = 35.0    # ...but never more than this
    STALL_TICKS = 100   # ~1 s at under a third of commanded speed -> give up
    BRAKE_HOLD = 2.0    # PWM per degree of heading error while braking (max 15)
    BRAKE_FF_CUT = 0.04 # m/s too fast -> drop the forward PWM, let feedback brake...
    BRAKE_FF_BELOW = 0.10  # ...but only while slowing to a stop (wheel asked < this).
                        # With ~3070 ticks/m the measured speed jitters +-0.03 m/s, and
                        # the cut fired mid-corridor: PWM 70 -> -5 -> 70 every few ticks
                        # (move(2), 23 Oct) = the wobble that steered into the wall.
    SPEED_FILTER = 0.25 # low-pass on the measured wheel speeds (coarser encoders now)
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
    BRAKE_FF_BELOW = 0.0
    SPEED_FILTER = 0.4
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
TURN_POS_GAIN = 3.0           # m/s of correction per m of creep during a turn
TURN_NEAR_DEG = 2.5           # within this of the target for...
TURN_NEAR_TICKS = 25          # ...this many ticks (~0.3 s) = turn finished


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
        self.raw_l = self.raw_c = self.raw_r = 8190.0   # unfiltered ToF
        self.hold_l = self.hold_c = self.hold_r = 0
        # Side-wall reading when centred: LEARNT whenever the mouse stands in
        # a cell with walls on both sides ((L+R)/2 doesn't depend on where in
        # the cell it is). The start readings (49/29) were far below the
        # calibrated 100, and a wrong value steers the mouse into a wall.
        self.side_nom = SIDE_NOMINAL_MM
        self.side_valid = SIDE_VALID_MM
        self.side_wall = SIDE_WALL_MM
        self.nom_samples = 0
        self.unsticks = 0
        self.overruns = 0
        self.med = (0, 0, 0)
        self.front_learns = 0
        self.backoffs = 0
        self.votes = (0, 0, 0)
        self.driving = False        # True only during straight moves (front hold)
        self.left_ok = not LEFT_FROM_GYRO   # left encoder seen counting?
        self.left_seen = 0        # last read_walls medians (for the log)

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
        self.rate = (uct_mouse.get_gyro() - self.gyro_bias) * GYRO_SCALE   # deg/s
        self.theta += self.rate * dt
        if not self.left_ok:
            if dl != 0:
                self.left_seen += abs(dl)
                if self.left_seen > 30:
                    self.left_ok = True        # the left encoder works after all
            if not self.left_ok:
                # left wheel distance from the right wheel and the gyro
                dl = (dr / TICKS_R - math.radians(self.rate) * dt * 2.0 * HALF_AXLE_M) * TICKS_L
        # low-passed wheel speeds (encoder counts are coarse at 10 ms)
        self.v_l += SPEED_FILTER * (dl / TICKS_L / dt - self.v_l)
        self.v_r += SPEED_FILTER * (dr / TICKS_R / dt - self.v_r)

        t = uct_mouse.get_tof()
        self.raw_l, self.raw_c, self.raw_r = t[TOF_L], t[TOF_C], t[TOF_R]
        # Bridge short dropouts: a sensor that was close to a wall and
        # suddenly reads 8190 keeps its last value for a few ticks.
        r = self.raw_l
        if r >= DROPOUT_MM and self.tof_l < 300.0 and self.hold_l < DROPOUT_HOLD:
            self.hold_l += 1
        else:
            self.tof_l = r
            self.hold_l = 0
        r = self.raw_c
        if r >= DROPOUT_MM and ((self.driving and self.tof_c < FRONT_CLOSE_HOLD_MM) or
                                (self.tof_c < 300.0 and self.hold_c < DROPOUT_HOLD)):
            self.hold_c += 1
        else:
            self.tof_c = r
            self.hold_c = 0
        r = self.raw_r
        if r >= DROPOUT_MM and self.tof_r < 300.0 and self.hold_r < DROPOUT_HOLD:
            self.hold_r += 1
        else:
            self.tof_r = r
            self.hold_r = 0
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
    def read_walls(self, samples=WALL_SAMPLES):
        """Classify (left, front, right) walls from many raw readings.

        A side counts as a WALL when MORE THAN HALF of the readings are
        close (majority vote = median). The earlier '3 of 15' rule was for
        the noisy firmware, whose close readings often dropped out to 8190;
        on the current, clean firmware it turned a real opening into a wall
        (23 Oct: a left opening was mapped as wall and the mouse gave up).
        8190 (no echo) counts as far. Also learns the centred side reading."""
        ls = []
        cs = []
        rs = []
        for _ in range(samples):
            self.tick(0, 0)
            ls.append(self.raw_l)
            cs.append(self.raw_c)
            rs.append(self.raw_r)
        need = samples // 2 + 1
        left, sl, nl = self._wall_vote(ls, self.side_wall, need)
        front, sc, nc = self._wall_vote(cs, FRONT_WALL_MM, need)
        right, sr, nr = self._wall_vote(rs, self.side_wall, need)
        self.med = (sl, sc, sr)
        self.votes = (nl, nc, nr)       # close readings out of `samples` (for the log)
        if left and right:
            self._learn_side(sl, sr)
        return left, front, right

    @staticmethod
    def _wall_vote(vals, limit, need):
        close = [v for v in vals if v < limit]
        n = len(close)
        if n >= need:
            close.sort()
            return True, close[n // 2], n
        vals.sort()
        return False, min(vals[len(vals) // 2], 9999), n

    def _learn_side(self, l, r):
        avg = (l + r) / 2.0
        # Only learn from a convincing pair of walls: a short "opening"
        # reading (133) once dragged this from 66 to 75.
        if abs(avg - self.side_nom) > 15.0 or abs(l - r) > 40.0:
            return
        if self.nom_samples == 0:
            self.side_nom = avg
        else:
            self.side_nom += 0.3 * (avg - self.side_nom)
        self.nom_samples += 1
        self.side_valid = self.side_nom + (SIDE_VALID_MM - SIDE_NOMINAL_MM)
        self.side_wall = self.side_nom + (SIDE_WALL_MM - SIDE_NOMINAL_MM)

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
        if (BRAKE_FF_CUT is not None and abs(v_cmd) < BRAKE_FF_BELOW and
                (err * v_cmd) < 0 and abs(err) > BRAKE_FF_CUT):
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
        lv = self.tof_l < self.side_valid
        rv = self.tof_r < self.side_valid
        if lv and rv:
            return (self.tof_r - self.tof_l) / 2000.0
        if lv:
            return (self.side_nom - self.tof_l) / 1000.0
        if rv:
            return (self.tof_r - self.side_nom) / 1000.0
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
        self.driving = True
        try:
            self._drive_loop(s, s_end, s_cell, v_max, v_end, accel, use_front)
        finally:
            self.driving = False

    def _drive_loop(self, s, s_end, s_cell, v_max, v_end, accel, use_front):
        v = self.v_cmd
        decel = accel if DECEL is None else min(accel, DECEL)
        stall = 0
        y_f = None                    # filtered lateral offset
        rejected = 0
        # Wall edges use the RAW readings, but a change must last
        # EDGE_CONFIRM ticks (a dropout blip doesn't), is dated back to the
        # tick it started, and each edge position is used only once per move.
        st_l = self.raw_l < self.side_valid
        st_r = self.raw_r < self.side_valid
        cnt_l = cnt_r = 0
        s_chg_l = s_chg_r = 0.0
        used = []
        front_fix = False
        driven = 0.0                  # encoder distance actually driven
        allowed = OVERRUN * (s_end - s) + OVERRUN_M
        corr0 = self.yaw_corr
        unsticks = 0
        touch = 0
        for _ in range(int(20 * (s_end - s) / 0.2 / max(v_max, 0.05)) + 300):
            s_at = None
            now = self.raw_l < self.side_valid
            if now == st_l:
                cnt_l = 0
            else:
                if cnt_l == 0:
                    s_chg_l = s
                cnt_l += 1
                if cnt_l >= EDGE_CONFIRM:
                    st_l = now
                    cnt_l = 0
                    s_at = s_chg_l
            now = self.raw_r < self.side_valid
            if now == st_r:
                cnt_r = 0
            else:
                if cnt_r == 0:
                    s_chg_r = s
                cnt_r += 1
                if cnt_r >= EDGE_CONFIRM:
                    st_r = now
                    cnt_r = 0
                    if s_at is None:
                        s_at = s_chg_r
            if s_at is not None:
                half = CELL_M * 500.0                             # 100 mm
                k = round((s_at * 1000.0 - (half - SENSOR_AHEAD_MM)) / (2 * half))
                s_edge = (k * 2 * half + half - SENSOR_AHEAD_MM) / 1000.0
                err = s_edge - s_at
                if k not in used and abs(err) < EDGE_SNAP_MM / 1000.0:
                    used.append(k)
                    # The error built up over `since_fix` metres tells us how
                    # much the encoders over/under-read: learn that ratio.
                    if self.since_fix > 0.08:
                        ratio = 1.0 + err / self.since_fix
                        self.odo_scale = clamp(self.odo_scale * (1.0 + 0.5 * (ratio - 1.0)),
                                               ODO_SCALE_MIN, ODO_SCALE_MAX)
                    self.since_fix = 0.0
                    self.edge_fixes += 1
                    self.edge_err_sum += abs(err)
                    s += err

            # front wall of the last cell -> exact distance to its centre
            # (not in the last ~1 cm: very close to a wall the front sensor
            # reads LONGER again - 55 with the nose almost touching - which
            # would make the fix push the mouse further in)
            if (use_front and FRONT_STOP_MM + FRONT_FIX_MIN_MM < self.tof_c < FRONT_TRUST_MM
                    and s_cell - s < 0.25):
                s_tof = s_cell - (self.tof_c - FRONT_STOP_MM) / 1000.0
                if abs(s_tof - s) < FRONT_FIX_GATE:
                    # First good look at the wall after a long stretch: the
                    # gap between where the encoders say we are and where the
                    # wall says we are is odometry error - learn from it
                    # (same as the wall-edge learner). With only the right
                    # encoder working this is what keeps cells 20 cm long.
                    if FRONT_LEARN and self.since_fix > 0.15 and self.tof_c < 220.0:
                        ratio = 1.0 + (s_tof - s) / self.since_fix
                        self.odo_scale = clamp(self.odo_scale * (1.0 + 0.3 * (ratio - 1.0)),
                                               ODO_SCALE_MIN, ODO_SCALE_MAX)
                        self.front_learns += 1
                    s += FRONT_BLEND * (s_tof - s)
                    front_fix = True
                    # This is a position fix too: restart the slip learner
                    # from here, or the jump would be mistaken for slip.
                    self.since_fix = 0.0
            rem = s_end - s
            if driven > allowed:
                self.overruns += 1                 # safety net: never run on
                break
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

            yaw_err_deg = wrap180(self.target_yaw - self.yaw())
            if self.raw_l < SIDE_TOUCH_MM or self.raw_r < SIDE_TOUCH_MM:
                touch += 1
            else:
                touch = 0
            if (BUMP_DEG is not None and unsticks < MAX_UNSTICKS and
                    (abs(yaw_err_deg) > BUMP_DEG or stall > BUMP_STALL_TICKS or touch >= 5)):
                # Knocked into a wall: back out, square up, carry on.
                unsticks += 1
                back = self._unstick()
                s += back
                driven += back
                v = 0.0
                stall = 0
                touch = 0
                y_f = None
                st_l = self.raw_l < self.side_valid
                st_r = self.raw_r < self.side_valid
                cnt_l = cnt_r = 0
                continue
            omega = K_HEADING * math.radians(yaw_err_deg)
            y = self._lateral_offset()
            if y is None:
                y_f = None
            else:
                if y_f is None:
                    y_f = y
                    rejected = 0
                elif abs(y - y_f) < LAT_OUTLIER_M:
                    y_f += LAT_FILTER * (y - y_f)
                    rejected = 0
                else:
                    # one wild reading: ignore it - but if it persists it's
                    # real (e.g. a wall appeared/ended): start again from it
                    rejected += 1
                    if rejected >= 5:
                        y_f = y
                        rejected = 0
                omega -= K_LATERAL * y_f
                self.yaw_corr = clamp(self.yaw_corr + math.degrees(K_ALIGN * y_f * self.dt),
                                      corr0 - YAW_CORR_MAX, corr0 + YAW_CORR_MAX)

            ds = self._wheels(v, omega)
            s += ds
            driven += ds
            self.since_fix += ds
        self.v_cmd = v
        self.late = max(0.0, s - s_end)        # how far past the handover point
        if v_end <= 0.0:
            self.stop()
            if front_fix:
                self.since_fix = 0.0  # we stopped at a measured distance from a wall
            if use_front:
                self._back_off()

    def _back_off(self):
        """Self-correction after a stop: if we ended up too close to the wall
        in front, reverse slowly (holding the heading) until the front
        reading is back near the centred value. At most 3 cm."""
        c = self._front_median()
        if not (BACKOFF_ABOVE_MM < c < BACKOFF_BELOW_MM):
            return
        self.backoffs += 1
        back = 0.0
        for _ in range(120):
            yaw_err = math.radians(wrap180(self.target_yaw - self.yaw()))
            back += self._wheels(-0.05, K_HEADING * yaw_err)
            if self.tof_c >= FRONT_STOP_MM - 2.0 or back < -0.03:
                break
        self.v_cmd = 0.0
        self.stop()

    def _front_median(self, n=5):
        vals = []
        for _ in range(n):
            self.tick(0, 0)
            vals.append(self.raw_c)
        vals.sort()
        return vals[n // 2]

    def _unstick(self):
        """Bump recovery: stop, reverse BACKUP_M straight out (no steering -
        the wall is right there), then turn back to the corridor heading.
        Returns the (negative) distance moved."""
        self.unsticks += 1
        self.stop()
        back = 0.0
        for _ in range(150):
            back += self._wheels(-BACKUP_V, 0.0)
            if back <= -BACKUP_M:
                break
        self.v_cmd = 0.0
        self.stop()
        self._rotate_to(self.target_yaw)
        return back

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
        return (dl / TICKS_L + dr / TICKS_R) / 2.0 * self.odo_scale

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
        fwd = 0.0         # how far the centre has crept forward (+) / back (m)
        near = 0          # ticks spent within TURN_NEAR_DEG of the target
        for _ in range(timeout_ticks):
            err = yaw_target - self.yaw()       # deg (can be up to 360 for the pirouette)
            a = abs(err)
            if a < TURN_DONE_DEG and abs(self.rate) < TURN_DONE_RATE:
                settled += 1
                if settled >= 3:
                    break
            else:
                settled = 0
            # Don't hunt for the last degree forever (23 Oct: up to 4 s per
            # turn, wiggling): close enough for long enough = done. The walls
            # re-align the heading on the next straight anyway.
            if a < TURN_NEAR_DEG:
                near += 1
                if near >= TURN_NEAR_TICKS:
                    break
            w_mag = min(TURN_W_MAX, abs(w) + TURN_ALPHA * 2.0 * self.dt,
                        math.sqrt(2.0 * TURN_ALPHA * a))
            w_mag = max(w_mag, TURN_W_MIN) if a > TURN_DONE_DEG else 0.0
            w = w_mag if err > 0 else -w_mag
            # Position hold: unequal wheels made the mouse creep ~1-2 cm
            # forward per turn (23 Oct) and its back hit the wall. Drive the
            # creep back to zero while spinning.
            # (only during the main part of the spin - near the end it made
            # the mouse shuffle back and forth)
            v = 0.0
            if a > 15.0:
                v = clamp(-TURN_POS_GAIN * fwd, -0.025, 0.025)
            fwd += self._wheels(v, math.radians(w))
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
