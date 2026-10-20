# =========================================================================
# offline_test.py  -  Test the maze "brain" WITHOUT the robot or simulator
# =========================================================================
# Uses the course's own maze generator (tools/physics_sim.py) to build the
# exact mazes the autograder uses, then drives a perfect "fake robot" through
# them with maze_logic.py. No motors, no physics: if the logic is wrong here,
# it will be wrong on the real mouse too.
#
# Run from the repo root (C:\Users\eesha\UCT-Micromouse):
#   python workspace/maze_lab/offline_test.py                     # seed 42, 4x6
#   python workspace/maze_lab/offline_test.py --seed 44           # one test maze
#   python workspace/maze_lab/offline_test.py --rows 8 --cols 8 --seed 48
#   python workspace/maze_lab/offline_test.py --tests             # all 5 graded seeds
#   python workspace/maze_lab/offline_test.py --sweep 500         # 500 random mazes
#
# Lives OUTSIDE final_task/ so the packager doesn't zip it into your submission.
# =========================================================================

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "workspace", "final_task"))   # maze_logic.py
sys.path.insert(0, os.path.join(REPO, "tools"))

from maze_logic import (MazeMap, NORTH, EAST, SOUTH, WEST, DX, DY, DIR_NAMES,
                        UNKNOWN, WALL, OPEN, opposite, left_of, right_of)

# physics_sim imports numpy + pygame at the top. The maze generator itself
# doesn't use pygame, so if it's missing we substitute an empty placeholder.
try:
    import pygame  # noqa: F401
except ImportError:
    import types
    sys.modules["pygame"] = types.ModuleType("pygame")
from physics_sim import generate_random_maze

CELL = 0.20
GRADED_TESTS = [(4, 6, 42), (4, 6, 43), (4, 6, 44), (4, 6, 45), (8, 8, 48)]

# Rough placeholder timings - replace with measured values after Step 2.
EST_EXPLORE_CELL_S = 1.0
EST_TURN_S = 0.8


# -------------------------------------------------------------------------
# 1. Turn the course generator's output into a "true" wall map
# -------------------------------------------------------------------------
def build_true_maze(rows, cols, seed):
    """generate_random_maze returns line segments in metres, e.g.
    ((0.4, 0.2), (0.4, 0.4)) = a vertical wall on the line x = 0.4 m.
    It only returns INTERNAL walls (the simulator adds the boundary itself)
    plus (cx, cy): the 2x2 room covers cells (cx-1..cx, cy-1..cy).
    We convert that into a fully-known MazeMap to act as 'reality'."""
    segments, (cx, cy) = generate_random_maze(rows, cols, CELL, seed=seed)

    truth = MazeMap(rows, cols)
    for y in range(rows):
        for x in range(cols):
            for d in range(4):
                if truth.walls[y][x][d] == UNKNOWN:
                    truth.walls[y][x][d] = OPEN

    for (x1, y1), (x2, y2) in segments:
        if abs(x1 - x2) < 1e-9:
            # Vertical wall on grid line x = c, spanning row r.
            c = int(round(x1 / CELL))
            r = int(round(min(y1, y2) / CELL))
            truth.set_wall(c, r, WEST, WALL)       # also sets EAST of (c-1, r)
        else:
            # Horizontal wall on grid line y = r, spanning column c.
            r = int(round(y1 / CELL))
            c = int(round(min(x1, x2) / CELL))
            truth.set_wall(c, r, SOUTH, WALL)      # also sets NORTH of (c, r-1)

    room = (cx - 1, cy - 1)                        # bottom-left, our convention
    return truth, room


# -------------------------------------------------------------------------
# 2. A "perfect" fake robot: exact sensing, exact moves, counts its effort
# -------------------------------------------------------------------------
class FakeRobot:
    def __init__(self, truth):
        self.truth = truth
        self.x, self.y, self.heading = 0, 0, EAST
        self.cells_moved = 0
        self.quarter_turns = 0
        self.trail = [(0, 0)]

    def sense(self):
        """What ideal ToF sensors would report: (left, front, right) walls."""
        w = self.truth.walls[self.y][self.x]
        h = self.heading
        return w[left_of(h)] == WALL, w[h] == WALL, w[right_of(h)] == WALL

    def turn_to(self, d):
        diff = (d - self.heading) % 4
        self.quarter_turns += 2 if diff == 2 else (0 if diff == 0 else 1)
        self.heading = d

    def step(self, d):
        self.turn_to(d)
        if self.truth.walls[self.y][self.x][d] != OPEN:
            raise RuntimeError("CRASH: drove into a wall at (%d,%d) heading %s"
                               % (self.x, self.y, DIR_NAMES[d]))
        self.x += DX[d]
        self.y += DY[d]
        self.cells_moved += 1
        self.trail.append((self.x, self.y))

    def follow(self, path):
        for d in MazeMap.path_to_headings(path):
            self.step(d)


# -------------------------------------------------------------------------
# 3. The mission logic (this is what main.py will do with a real robot)
# -------------------------------------------------------------------------
def run_mission(rows, cols, seed, verbose=False):
    truth, true_room = build_true_maze(rows, cols, seed)
    maze = MazeMap(rows, cols)
    bot = FakeRobot(truth)
    r = {"rows": rows, "cols": cols, "seed": seed, "true_room": true_room}

    # ---- Phase 1: explore until we are standing in a confirmed room ----
    room = None
    while True:
        left, front, right = bot.sense()
        maze.record_cell(bot.x, bot.y, bot.heading, left, front, right)

        room = maze.find_target_room()
        if room is not None:
            break                       # certain: interior open + 1 entrance

        path = maze.path_to_nearest_unvisited(bot.x, bot.y, bot.heading)
        if path is None:
            room = maze.find_target_room(final=True)   # best guess fallback
            break                       # explored everything reachable
        bot.step(MazeMap.path_to_headings(path)[0])   # ONE cell, then re-plan

    # The last perimeter wall can be seen from a cell just outside the room,
    # so make sure we are standing inside it before the pirouette.
    if room is not None and not maze.in_room(bot.x, bot.y, room):
        bot.follow(maze.shortest_path((bot.x, bot.y), maze.room_cells(*room), bot.heading))

    r["explore_cells"] = bot.cells_moved
    r["explore_turns"] = bot.quarter_turns
    r["found_room"] = room
    r["room_correct"] = (room == true_room)
    r["cells_visited"] = sum(sum(row) for row in maze.visited)
    r["explore_map"] = maze
    r["explore_trail"] = list(bot.trail)
    if room is None:
        return r

    # ---- Phase 2: pirouette (just a check here: are we inside the room?) ----
    r["pirouette_in_room"] = maze.in_room(bot.x, bot.y, true_room)

    # ---- Phase 3: shortest KNOWN path back to (0,0), then face East ----
    back = maze.shortest_path((bot.x, bot.y), [(0, 0)], bot.heading)
    r["return_cells"] = len(back) - 1
    bot.follow(back)
    bot.turn_to(EAST)

    # ---- Phase 4: sprint plan from (0,0) into the room ----
    sprint = maze.shortest_path((0, 0), maze.room_cells(*room), EAST)
    true_best = truth.shortest_path((0, 0), truth.room_cells(*true_room), EAST)
    r["sprint_path"] = sprint
    r["sprint_cells"] = len(sprint) - 1
    r["true_best_cells"] = len(true_best) - 1
    r["sprint_segments"] = MazeMap.compress(MazeMap.path_to_headings(sprint))
    r["truth"] = truth
    return r


# -------------------------------------------------------------------------
# 4. ASCII drawing (works in PowerShell - plain characters only)
# -------------------------------------------------------------------------
def draw(maze, room=None, path=None, title=""):
    """  +---+  wall   +   +  open   + . +  unknown (horizontal)
         |      wall   (space) open  :      unknown (vertical)
         S start   R room   * sprint path   # visited   (blank) not visited"""
    on_path = set(path) if path else set()
    hz = {WALL: "---", OPEN: "   ", UNKNOWN: " . "}
    vt = {WALL: "|", OPEN: " ", UNKNOWN: ":"}
    lines = [title] if title else []
    for y in range(maze.rows - 1, -1, -1):
        top = "+"
        mid = vt[maze.walls[y][0][WEST]]
        for x in range(maze.cols):
            top += hz[maze.walls[y][x][NORTH]] + "+"
            if (x, y) == (0, 0):
                ch = "S"
            elif (x, y) in on_path:
                ch = "*"
            elif room and maze.in_room(x, y, room):
                ch = "R"
            elif maze.visited[y][x]:
                ch = "#"
            else:
                ch = " "
            mid += " " + ch + " " + vt[maze.walls[y][x][EAST]]
        lines.append(top)
        lines.append(mid)
    lines.append("+" + "---+" * maze.cols)
    print("\n".join(lines))


def report(r):
    print("\n=== %dx%d maze, seed %d ===" % (r["rows"], r["cols"], r["seed"]))
    draw(r["explore_map"], r["found_room"], None,
         "Robot's map at the end of exploration (#=visited, R=room):")
    if r["found_room"] is None:
        print("!! Room NOT found. True room bottom-left:", r["true_room"])
        return
    names = ["%s x%d" % (DIR_NAMES[d], n) for d, n in r["sprint_segments"]]
    t_est = r["explore_cells"] * EST_EXPLORE_CELL_S + r["explore_turns"] * EST_TURN_S
    print("Room found at %s (correct: %s), pirouette inside room: %s"
          % (r["found_room"], r["room_correct"], r["pirouette_in_room"]))
    print("Exploration: %d cell moves, %d quarter-turns, %d/%d cells visited  (~%.0f s est.)"
          % (r["explore_cells"], r["explore_turns"], r["cells_visited"],
             r["rows"] * r["cols"], t_est))
    print("Return to start: %d cells" % r["return_cells"])
    print("Sprint: %d cells (true optimum %d) -> %s"
          % (r["sprint_cells"], r["true_best_cells"], ", ".join(names)))
    draw(r["truth"], r["true_room"], r["sprint_path"],
         "True maze with sprint path (*):")


def sweep(n, rows, cols):
    fails, wrong_room, outside, suboptimal = [], [], [], []
    worst = (0, None)
    for seed in range(1000, 1000 + n):
        try:
            r = run_mission(rows, cols, seed)
        except RuntimeError as e:
            fails.append((seed, str(e)))
            continue
        if r["found_room"] is None:
            fails.append((seed, "room not found"))
            continue
        if not r["room_correct"]:
            wrong_room.append(seed)
        if not r["pirouette_in_room"]:
            outside.append(seed)
        if r["sprint_cells"] > r["true_best_cells"]:
            suboptimal.append(seed)
        if r["explore_cells"] > worst[0]:
            worst = (r["explore_cells"], seed)
    print("\n=== Sweep: %d random %dx%d mazes (seeds 1000-%d) ===" % (n, rows, cols, 999 + n))
    print("Crashes / room not found : %d %s" % (len(fails), fails[:5]))
    print("Wrong (fake) room chosen : %d %s" % (len(wrong_room), wrong_room[:10]))
    print("Pirouette outside room   : %d" % len(outside))
    print("Sprint longer than optimum (unexplored shortcut): %d %s"
          % (len(suboptimal), suboptimal[:10]))
    print("Longest exploration      : %d cell moves (seed %s)" % worst)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tests", action="store_true", help="run all 5 graded seeds")
    p.add_argument("--sweep", type=int, default=0, help="run N random mazes")
    a = p.parse_args()

    if a.sweep:
        sweep(a.sweep, a.rows, a.cols)
    elif a.tests:
        for rows, cols, seed in GRADED_TESTS:
            report(run_mission(rows, cols, seed))
    else:
        report(run_mission(a.rows, a.cols, a.seed))
