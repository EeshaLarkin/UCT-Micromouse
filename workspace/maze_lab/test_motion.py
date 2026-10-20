# =========================================================================
# test_motion.py  -  Test motion.py in the course simulator on a KNOWN route
# =========================================================================
# No exploration logic here: we already know the true maze (from the course
# generator), so we plan a route on it and check that motion.py can drive it
# without crashing, and that read_walls() agrees with the real walls.
#
# Run from the repo root (C:\Users\eesha\UCT-Micromouse):
#   python workspace/maze_lab/test_motion.py --seed 42             # tour every cell
#   python workspace/maze_lab/test_motion.py --seed 42 --sprint    # fast run to room
#   python workspace/maze_lab/test_motion.py --seed 48 --rows 8 --cols 8
#   add --headless to skip the simulator window, --imbalance/--slip to stress it
#
# The script starts the simulator itself, runs the robot as a second process
# (exactly like the autograder does), then reads the simulator's ground-truth
# log to tell you if/where it crashed.
# =========================================================================

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FINAL = os.path.join(REPO, "workspace", "final_task")
TRAJ = os.path.join(tempfile.gettempdir(), "test_motion_traj.json")
SIMLOG = os.path.join(tempfile.gettempdir(), "test_motion_sim.log")


# -------------------------------------------------------------------------
# Part 1: the launcher (runs on your laptop, starts sim + robot)
# -------------------------------------------------------------------------
def sim_config(rows, cols):
    """physics_sim.py lets the config file's maze size OVERRIDE --rows/--cols
    (course-tool bug), so write a copy of the config with the size we want."""
    cfg = json.load(open(os.path.join(REPO, "tools", "simulation_config.json")))
    cfg.setdefault("maze", {})
    cfg["maze"]["grid_rows"] = rows
    cfg["maze"]["grid_cols"] = cols
    path = os.path.join(tempfile.gettempdir(), "test_motion_config.json")
    json.dump(cfg, open(path, "w"), indent=2)
    return path


def launch(a):
    sim_cmd = [sys.executable, os.path.join(REPO, "tools", "physics_sim.py"),
               "--map", "random", "--seed", str(a.seed),
               "--rows", str(a.rows), "--cols", str(a.cols),
               "--imbalance", str(a.imbalance), "--slip", str(a.slip),
               "--json-log", TRAJ, "--max-time", "300",
               "--config", sim_config(a.rows, a.cols)]
    if a.headless:
        sim_cmd.append("--headless")
    if os.path.exists(TRAJ):
        os.remove(TRAJ)
    log = open(SIMLOG, "w")
    sim = subprocess.Popen(sim_cmd, stdout=log, stderr=log, cwd=REPO)
    for _ in range(200):                       # wait until it's listening
        time.sleep(0.05)
        with open(SIMLOG) as f:
            if "Waiting for student script" in f.read():
                break
    else:
        print("Simulator did not start - see", SIMLOG)
        sim.kill()
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([FINAL, HERE, os.path.join(REPO, "python")])
    if a.headless:
        env["GRADESCOPE_AUTOGRADER"] = "1"     # run the sim as fast as possible
    client = [sys.executable, os.path.abspath(__file__), "--client"] + sys.argv[1:]
    subprocess.call(client, env=env, cwd=FINAL)

    try:
        sim.wait(timeout=15)
    except subprocess.TimeoutExpired:
        sim.terminate()
    log.close()

    if not os.path.exists(TRAJ):
        print("No simulator log found (", TRAJ, ")")
        return
    d = json.load(open(TRAJ))
    print("\n--- Simulator ground truth ---")
    print("Crashed into a wall : %s" % ("YES" if d.get("crashed") else "no"))
    print("Simulated time      : %.1f s" % d.get("time", 0))
    fx, fy = d.get("final_x", 0), d.get("final_y", 0)
    print("Final pose          : x=%.3f y=%.3f theta=%.1f deg"
          % (fx, fy, math.degrees(d.get("final_theta", 0))))
    cx, cy = int(fx / 0.2), int(fy / 0.2)
    print("Offset from centre of cell (%d,%d): %+.0f mm, %+.0f mm"
          % (cx, cy, (fx - (cx + 0.5) * 0.2) * 1000, (fy - (cy + 0.5) * 0.2) * 1000))

    # Where did the robot actually stop each time? (points that didn't move)
    tr = d.get("trajectory", [])
    worst = 0.0
    for i in range(1, len(tr)):
        if math.hypot(tr[i][0] - tr[i - 1][0], tr[i][1] - tr[i - 1][1]) < 0.001:
            ox = (tr[i][0] % 0.2 - 0.1) * 1000
            oy = (tr[i][1] % 0.2 - 0.1) * 1000
            worst = max(worst, math.hypot(ox, oy))
    print("Worst stop offset from a cell centre: %.0f mm  (corner clearance ~30 mm)" % worst)

    if a.sprint and d.get("target_room"):
        # Same measurement as the grader: leave 0.15 m of start -> within 0.28 m of room centre
        rx, ry = d["target_room"][0] * 0.2, d["target_room"][1] * 0.2
        pts = [p for p in tr if len(p) >= 4]
        i0 = next((i for i, p in enumerate(pts) if math.hypot(p[0] - 0.1, p[1] - 0.1) > 0.15), None)
        i1 = next((i for i, p in enumerate(pts) if i0 is not None and i > i0
                   and math.hypot(p[0] - rx, p[1] - ry) <= 0.28), None)
        if i0 is not None and i1 is not None:
            dist = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
                       for k in range(i0 + 1, i1 + 1))
            secs = max(0.5, pts[i1][3] - pts[i0][3])
            print("Grader-style sprint speed: %.3f m/s  (5 bonus pts at >= 0.30)" % (dist / secs))


# -------------------------------------------------------------------------
# Part 2: the robot (runs as the simulator's "student script")
# -------------------------------------------------------------------------
def turn_amount(heading, d):
    q = (d - heading) % 4
    return {0: 0, 1: 1, 2: 2, 3: -1}[q]


def tour(truth, start=(0, 0)):
    """Depth-first walk that visits every cell and backtracks (like a
    worst-case exploration): returns the list of cells in driving order."""
    from maze_logic import DX, DY
    seen = {start}
    seq = [start]

    def go(c):
        for d in (1, 0, 3, 2):
            if truth.walls[c[1]][c[0]][d] != 2:      # 2 = OPEN
                continue
            n = (c[0] + DX[d], c[1] + DY[d])
            if n in seen:
                continue
            seen.add(n)
            seq.append(n)
            go(n)
            seq.append(c)
    go(start)
    return seq


def client(a):
    import uct_mouse
    from maze_logic import MazeMap, EAST, WALL, left_of, right_of, DIR_NAMES
    from motion import Motion
    from offline_test import build_true_maze

    if not uct_mouse.init():
        print("uct_mouse.init() failed")
        return
    uct_mouse.set_polarity(1, 1)
    uct_mouse.delay_ms(20)          # let the first sensor packet arrive
    rows, cols = uct_mouse.get_maze_dimensions()
    print("Maze dimensions from simulator:", rows, "x", cols)
    truth, room = build_true_maze(rows, cols, a.seed)

    m = Motion()
    m.calibrate_gyro()
    x, y, heading = 0, 0, EAST
    t0 = m.ticks

    if a.sprint:
        path = truth.shortest_path((0, 0), truth.room_cells(*room), EAST)
        segs = MazeMap.compress(MazeMap.path_to_headings(path))
        print("Sprint plan:", ", ".join("%s x%d" % (DIR_NAMES[d], n) for d, n in segs))
        for d, n in segs:
            m.turn(turn_amount(heading, d), fast_pwm=a.turnpwm)
            heading = d
            m.move(n, v_max=a.vmax, accel=a.accel)
        secs = (m.ticks - t0) * 0.01
        print("Sprint: %d cells in %.1f s -> average %.3f m/s (grader wants >= 0.30)"
              % (len(path) - 1, secs, (len(path) - 1) * 0.2 / secs))
        return

    route = tour(truth)
    print("Touring %d cells with %d one-cell moves" % (rows * cols, len(route) - 1))
    wrong = 0
    for i in range(1, len(route)):
        nx, ny = route[i]
        d = MazeMap.path_to_headings([(x, y), (nx, ny)])[0]
        m.turn(turn_amount(heading, d))
        heading = d
        m.move(1, v_max=a.vmax)
        x, y = nx, ny
        seen = m.read_walls()
        w = truth.walls[y][x]
        real = (w[left_of(heading)] == WALL, w[heading] == WALL, w[right_of(heading)] == WALL)
        if seen != real:
            wrong += 1
            print("  wall mismatch at (%d,%d) facing %s: saw L/F/R=%s, real=%s  tof=%d/%d/%d"
                  % (x, y, DIR_NAMES[heading], seen, real, m.tof_l, m.tof_c, m.tof_r))
    secs = (m.ticks - t0) * 0.01
    print("Done: %d moves, %d wall-reading mismatches, %.1f s (%.2f s per move)"
          % (len(route) - 1, wrong, secs, secs / (len(route) - 1)))
    if m.turns_done:
        print("Turn accuracy: mean %.1f deg, worst %.1f deg"
              % (m.turn_err_sum / m.turns_done, m.turn_err_max))
    print("Heading correction learnt from walls: %+.1f deg, odometry scale learnt: %.3f" % (m.yaw_corr, m.odo_scale))
    if m.edge_fixes:
        print("Wall-edge position fixes: %d (average correction %.1f mm)"
              % (m.edge_fixes, 1000 * m.edge_err_sum / m.edge_fixes))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--client", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--imbalance", type=float, default=0.06)
    p.add_argument("--slip", type=float, default=0.04)
    p.add_argument("--vmax", type=float, default=None, help="cruise speed m/s")
    p.add_argument("--accel", type=float, default=None, help="m/s^2 for straights")
    p.add_argument("--turnpwm", type=int, default=70, help="fast turn PWM")
    p.add_argument("--sprint", action="store_true")
    p.add_argument("--headless", action="store_true")
    a = p.parse_args()
    if a.vmax is None:
        a.vmax = 0.38 if a.sprint else 0.25
    if a.accel is None:
        a.accel = 2.5 if a.sprint else 1.2
    if a.client:
        client(a)
    else:
        launch(a)
