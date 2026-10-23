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
from maze_logic import MazeMap, EAST, DIR_NAMES
from motion import Motion, ON_HARDWARE, TURN_FAST_PWM

# Speeds (m/s) and accelerations (m/s^2) for each phase
if ON_HARDWARE:
    # real mouse tops out at ~0.41 m/s (calibrate test 3): leave headroom
    # for steering. Start gentle; raise once driving is proven on the maze.
    EXPLORE_V = 0.20
    EXPLORE_A = 0.8
    RETURN_V = 0.25
    RETURN_A = 1.0
    SPRINT_V = 0.32
    SPRINT_A = 1.0
    SPRINT_ARC_V = 0.18
    # The curved corners were tuned on the simulator's 7 cm-radius body; the
    # real mouse is 14 x 12 cm, so it sprints with stop-and-turn corners
    # until curves are proven on the real maze.
    SPRINT_CURVES = False
    START_COUNTDOWN_S = 5        # time to put the mouse down after power-on
else:
    EXPLORE_V = 0.25
    EXPLORE_A = 1.2
    RETURN_V = 0.30
    RETURN_A = 1.5
    SPRINT_V = 0.38
    SPRINT_A = 1.5
    SPRINT_ARC_V = 0.22          # speed through curved corners (outer wheel ~1.5x this)
    SPRINT_CURVES = True
    START_COUNTDOWN_S = 0

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

    # ------------------------------------------------------------------
    # Driving along a planned path
    # ------------------------------------------------------------------
    def drive_path(self, path, v_max, accel, turn_pwm=TURN_FAST_PWM):
        """Follow a list of cells, merging straight runs into single moves:
        [E,E,E,N] becomes 'turn, drive 3 cells, turn, drive 1 cell'."""
        segs = MazeMap.compress(MazeMap.path_to_headings(path))
        for d, n in segs:
            self.m.turn(turn_amount(self.heading, d), turn_pwm)
            self.heading = d
            self.m.move(n, v_max=v_max, accel=accel)
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
            log("[Phase 2] Target recognised - 360 deg pirouette")
            self.m.pirouette()

        oled("3 Return")
        log("[Phase 3] Returning to (0,0)")
        back = self.maze.shortest_path((self.x, self.y), [(0, 0)], self.heading)
        if back is not None:
            self.drive_path(back, RETURN_V, RETURN_A)
        self.m.turn(turn_amount(self.heading, EAST))
        self.heading = EAST
        if self.room is None:
            return

        oled("4 Pause 3s")
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


def main():
    uct_mouse.init()               # (returns None on the real mouse)
    uct_mouse.set_motors(0, 0)
    uct_mouse.set_polarity(1, 1)
    uct_mouse.delay_ms(20)        # let the first sensor packet arrive
    for sec in range(START_COUNTDOWN_S, 0, -1):
        oled("Start in %d..." % sec)
        uct_mouse.delay_ms(1000)
    oled("Calibrating")
    try:
        rows, cols = maze_dimensions()
        MazeSolver(rows, cols).solve()
    except Exception as e:
        # never fail silently: show it on the OLED and save the details
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


if __name__ == "__main__":
    main()
