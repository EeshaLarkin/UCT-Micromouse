# =========================================================================
# main.py  -  UCT Micromouse 2026, Submission 4: "Search, Celebrate & Sprint"
# =========================================================================
# Ties the two layers together:
#   maze_logic.py  - the BRAIN: wall map, BFS planning, 2x2 room detection
#   motion.py      - the LEGS + EYES: closed-loop moves, turns, wall sensing
#
# Mission:
#   Phase 1  explore from (0,0) until the 2x2 target room is confirmed
#   Phase 2  360 deg clockwise pirouette inside the room
#   Phase 3  shortest known path back to (0,0), face East
#   Phase 4  pause 3.0 s, then sprint along the shortest path into the room
# =========================================================================

import sys
import uct_mouse
from maze_logic import MazeMap, EAST, DIR_NAMES, DX, DY
from motion import Motion, ON_HARDWARE, TURN_FAST_PWM, WALL_SAMPLES, SIDE_WALL_MM, FRONT_WALL_MM
from maze_logic import WALL, OPEN

# A side wall whose reading was this close to the wall/opening limit is
# "doubtful": real walls read ~60-80 when the mouse is centred, but a mouse
# stopped slightly off can see an opening's edge and read 90 (run 1, 23 Oct:
# a false wall sealed off half the maze and the mouse went home).
DOUBT_MM = SIDE_WALL_MM - 45.0

# Speeds (m/s) and accelerations (m/s^2) for each phase
if ON_HARDWARE:
    # real mouse tops out at ~0.41 m/s (calibrate test 3): leave headroom
    # for steering. Start gentle; raise once driving is proven on the maze.
    # 23 Oct firmware: top speed only ~0.24 m/s, so keep headroom for steering
    EXPLORE_V = 0.16
    EXPLORE_A = 0.8
    RETURN_V = 0.16           # first real run crashed on the return at 0.25;
    RETURN_A = 0.8            # exploration (0.20) worked, so match it for now
    SPRINT_V = 0.20
    SPRINT_A = 1.0
    SPRINT_ARC_V = 0.18
    # The curved corners were tuned on the simulator's 7 cm-radius body; the
    # real mouse is 14 x 12 cm, so it sprints with stop-and-turn corners
    # until curves are proven on the real maze.
    SPRINT_CURVES = False
else:
    EXPLORE_V = 0.25
    EXPLORE_A = 1.2
    RETURN_V = 0.30
    RETURN_A = 1.5
    SPRINT_V = 0.38
    SPRINT_A = 1.5
    SPRINT_ARC_V = 0.22          # speed through curved corners (outer wheel ~1.5x this)
    SPRINT_CURVES = True

VERBOSE = not ON_HARDWARE     # printing disturbs loop timing on the STM32


def log(*args):
    if VERBOSE:
        print(*args)


def oled(text):
    """Show the current phase on OLED row 1 (we can't print on the mouse)."""
    try:
        uct_mouse.display_text(1, text[:18])
    except Exception:
        pass


LOG_FILE = "mission_log.txt"     # flight recorder (real mouse only)


def turn_amount(heading, d):
    """Quarter-turns from heading to d: +1 right, -1 left, 2 about-face."""
    return (0, 1, 2, -1)[(d - heading) % 4]


class MazeSolver:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.maze = MazeMap(rows, cols)
        self.m = Motion()
        self.x = 0
        self.y = 0
        self.heading = EAST           # start pose: (0,0) facing East
        self.room = None
        self.phase = 1
        self.doubts = []              # (x, y, dir) side walls worth a second look
        self.t0 = uct_mouse.get_ticks_ms() if hasattr(uct_mouse, "get_ticks_ms") else 0
        if ON_HARDWARE:
            try:
                with open(LOG_FILE, "w") as f:
                    f.write("time  phase cell  heading move  tof L/C/R  heading_err  side_nom bumps overruns odo_scale backoffs\n")
            except Exception:
                pass

    def trace(self, what):
        """Flight recorder: one line per move, written while stopped, so after
        a crash the last lines show where the mouse was and what it saw."""
        if not ON_HARDWARE:
            return
        try:
            t = 0.0
            if hasattr(uct_mouse, "get_ticks_ms"):
                t = (uct_mouse.get_ticks_ms() - self.t0) / 1000.0
            m = self.m
            with open(LOG_FILE, "a") as f:
                l, c, r = m.tof_l, m.tof_c, m.tof_r
                if what[:5] == "walls":
                    l, c, r = m.med            # the medians the decision used
                extra = ""
                if what[:5] == "walls":
                    extra = "  close %d/%d/%d of %d" % (m.votes + (WALL_SAMPLES,))
                f.write("%6.1f P%d (%d,%d) %s %-10s %4d/%4d/%4d %+5.1f  %3d %d %d odo%.2f b%d%s\n"
                        % (t, self.phase, self.x, self.y, DIR_NAMES[self.heading], what,
                           min(l, 9999), min(c, 9999), min(r, 9999),
                           m.target_yaw - m.yaw(), m.side_nom, m.unsticks, m.overruns,
                           m.odo_scale, m.backoffs, extra))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Driving along a planned path
    # ------------------------------------------------------------------
    def drive_path(self, path, v_max, accel, turn_pwm=TURN_FAST_PWM):
        """Follow a list of cells, merging straight runs into single moves:
        [E,E,E,N] becomes 'turn, drive 3 cells, turn, drive 1 cell'."""
        segs = MazeMap.compress(MazeMap.path_to_headings(path))
        for d, n in segs:
            q = turn_amount(self.heading, d)
            self.m.turn(q, turn_pwm)
            self.heading = d
            if q:
                self.trace("turn %+d" % q)
            self.m.move(n, v_max=v_max, accel=accel)
            self.x += DX[d] * n
            self.y += DY[d] * n
            self.trace("move %d" % n)
        if path:
            self.x, self.y = path[-1]

    def sweep(self, path, v_max, v_arc, accel):
        """Like drive_path, but corners are taken as curves without stopping."""
        segs = MazeMap.compress(MazeMap.path_to_headings(path))
        plan = []
        h = self.heading
        for d, n in segs:
            plan.append((n, turn_amount(h, d)))
            h = d
        self.m.sweep_path(plan, v_max, v_arc, accel)
        self.heading = h
        if path:
            self.x, self.y = path[-1]

    def sense(self):
        left, front, right = self.m.read_walls()
        self.maze.record_cell(self.x, self.y, self.heading, left, front, right)
        sl, _, sr = self.m.med
        if left and sl > DOUBT_MM:
            self.doubts.append((self.x, self.y, (self.heading + 3) % 4))
        if right and sr > DOUBT_MM:
            self.doubts.append((self.x, self.y, (self.heading + 1) % 4))
        self.trace("walls %s%s%s" % ("L" if left else "-", "F" if front else "-",
                                     "R" if right else "-"))

    # ------------------------------------------------------------------
    # Phase 1: exploration
    # ------------------------------------------------------------------
    def explore(self):
        """Frontier exploration: sense, check for the room, then drive to the
        nearest unvisited cell. Every cell on that BFS path except the last is
        already mapped, so the whole path is driven without stopping to sense
        (merged straights) and we only sense when we reach the new cell."""
        while True:
            self.sense()
            self.room = self.maze.find_target_room()
            if self.room is not None:
                log("[Phase 1] Room confirmed at", self.room)
                break
            path = self.maze.path_to_nearest_unvisited(self.x, self.y, self.heading)
            if path is None and self.recheck():
                continue                  # a doubtful wall was really open: explore on
            if path is None:
                self.room = self.maze.find_target_room(final=True)
                log("[Phase 1] Maze fully explored, best room guess:", self.room)
                break
            self.drive_path(path, EXPLORE_V, EXPLORE_A)

        # The last perimeter wall can be seen from just outside the room.
        if self.room is not None and not self.maze.in_room(self.x, self.y, self.room):
            path = self.maze.shortest_path((self.x, self.y),
                                           self.maze.room_cells(*self.room), self.heading)
            self.drive_path(path, EXPLORE_V, EXPLORE_A)

    def recheck(self):
        """Before giving up without a room: double-check every doubtful side
        wall that is hiding unvisited cells. Drive to its cell, turn to FACE
        it and measure it with the front sensor (the most reliable one).
        Returns True if one turned out to be open."""
        mz = self.maze
        while self.doubts:
            x, y, d = self.doubts.pop()
            nx, ny = x + DX[d], y + DY[d]
            if not mz.in_bounds(nx, ny) or mz.visited[ny][nx]:
                continue                  # nothing new behind it - doesn't matter
            if mz.get_wall(x, y, d) != WALL:
                continue
            path = mz.shortest_path((self.x, self.y), [(x, y)], self.heading)
            if path is None:
                continue
            self.drive_path(path, EXPLORE_V, EXPLORE_A)
            q = turn_amount(self.heading, d)
            self.m.turn(q)
            self.heading = d
            _, front, _ = self.m.read_walls()
            self.trace("recheck %s" % ("wall" if front else "OPEN"))
            if not front:
                mz.set_wall(x, y, d, OPEN)
                log("[Phase 1] Re-check: wall at", (x, y), DIR_NAMES[d], "is open")
                return True
        return False

    # ------------------------------------------------------------------
    # The whole mission
    # ------------------------------------------------------------------
    def solve(self):
        self.m.calibrate_gyro()

        oled("1 Explore %dx%d" % (self.rows, self.cols))
        log("[Phase 1] Exploring a %dx%d maze..." % (self.rows, self.cols))
        self.explore()
        if self.room is None:
            log("[Phase 1] No target room found - returning to start")
        else:
            oled("2 Pirouette")
            self.phase = 2
            log("[Phase 2] Target recognised - 360 deg pirouette")
            self.m.pirouette()
            self.trace("pirouette")

        oled("3 Return")
        self.phase = 3
        log("[Phase 3] Returning to (0,0)")
        back = self.maze.shortest_path((self.x, self.y), [(0, 0)], self.heading)
        if back is not None:
            self.drive_path(back, RETURN_V, RETURN_A)
        self.m.turn(turn_amount(self.heading, EAST))
        self.heading = EAST
        if self.room is None:
            return

        oled("4 Pause 3s")
        self.phase = 4
        log("[Phase 4] Pausing 3.0 s")
        for _ in range(300):
            self.m.tick(0, 0)         # keep the gyro integrating while we wait

        sprint = self.maze.shortest_path((0, 0), self.maze.room_cells(*self.room), EAST)
        segs = MazeMap.compress(MazeMap.path_to_headings(sprint))
        log("[Phase 4] Sprint:", ", ".join("%s x%d" % (DIR_NAMES[d], n) for d, n in segs))
        if SPRINT_CURVES:
            self.sweep(sprint, SPRINT_V, SPRINT_ARC_V, SPRINT_A)
        else:
            self.drive_path(sprint, SPRINT_V, SPRINT_A)
        oled("Done!")
        log("[Mission complete] Stopped inside the target room")


def maze_dimensions():
    """(rows, cols) of the arena, queried dynamically as the brief requires.
    Older mouse firmware doesn't have get_maze_dimensions() (it was added to
    the course firmware in October), so fall back to its alias, then to the
    standard 4 x 6 lab maze."""
    for name in ("get_maze_dimensions", "get_maze_size"):
        fn = getattr(uct_mouse, name, None)
        if fn is not None:
            try:
                rows, cols = fn()
                if rows >= 2 and cols >= 2:
                    return int(rows), int(cols)
            except Exception:
                pass
    return 4, 6


def wait_for_start():
    """Real mouse: wait for SW1 (the RESET button doesn't work), then give
    3 s to take your hand away. We don't know whether SW1 reads 1 or 0 when
    pressed, so wait for it to CHANGE from its power-on reading. If this
    firmware has no get_button(), fall back to a 10 s countdown."""
    button = getattr(uct_mouse, "get_button", None)
    base = None
    if button is not None:
        try:
            base = button()
        except Exception:
            base = None
    if base is None:
        for sec in range(10, 0, -1):
            oled("Start in %d..." % sec)
            uct_mouse.delay_ms(1000)
        return
    oled("Press SW1")
    held = 0
    while held < 3:                          # 3 readings in a row = pressed
        uct_mouse.delay_ms(10)
        held = held + 1 if button() != base else 0
    oled("Release SW1")
    for _ in range(300):                     # up to 3 s for the release
        uct_mouse.delay_ms(10)
        if button() == base:
            break
    for sec in range(3, 0, -1):
        oled("Start in %d..." % sec)
        uct_mouse.delay_ms(1000)


def run_once():
    """One complete mission. Any error stops the motors, shows ERROR on the
    OLED and is saved to mission_error.txt - never a silent failure."""
    oled("Calibrating")
    try:
        rows, cols = maze_dimensions()
        MazeSolver(rows, cols).solve()
    except Exception as e:
        uct_mouse.set_motors(0, 0)
        oled("ERROR: see file")
        if hasattr(sys, "print_exception"):
            sys.print_exception(e)                 # shows in mpremote over USB
        try:
            with open("mission_error.txt", "w") as f:
                if hasattr(sys, "print_exception"):
                    sys.print_exception(e, f)      # MicroPython
                else:
                    import traceback
                    traceback.print_exc(file=f)
        except Exception:
            pass
        if VERBOSE:
            raise
    finally:
        uct_mouse.set_motors(0, 0)   # never leave the motors running after an error


def main():
    uct_mouse.init()               # (returns None on the real mouse)
    uct_mouse.set_motors(0, 0)
    uct_mouse.set_polarity(1, 1)
    uct_mouse.delay_ms(20)        # let the first sensor packet arrive
    if not ON_HARDWARE:
        run_once()                 # simulator / autograder: just go
        return
    # Real mouse: press SW1 for each run. After a run (or a crash) it waits
    # for SW1 again, so you can put it back at the start and go again
    # without switching it off. mpremote can still interrupt it to upload.
    while True:
        wait_for_start()
        run_once()
        uct_mouse.delay_ms(500)
        try:
            import gc
            gc.collect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
