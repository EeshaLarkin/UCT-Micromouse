# =========================================================================
# memcheck.py  -  Will the solver fit and run fast enough on the STM32?
# =========================================================================
# Desk test, MOTORS STAY OFF. Copy to the UCT_MMOUSE drive together with
# maze_logic.py, motion.py and final_task/main.py RENAMED to mission.py
# (so it doesn't start driving at power-on). Then, plugged in:
#
#     mpremote resume exec "import memcheck"
#
# Reports: MicroPython / .mpy version, free RAM after importing each module,
# how big the maze map gets for 4x6 / 8x8 / 16x16 and how long planning takes,
# and the REAL control-loop period (10 ms delay + our own code).
# =========================================================================

import gc
import sys
import time

def free():
    gc.collect()
    return gc.mem_free()

def line(label, before=None):
    f = free()
    if before is None:
        print("%-34s free %6d bytes" % (label, f))
    else:
        print("%-34s free %6d bytes  (used %d)" % (label, f, before - f))
    return f

print("=== memcheck ===")
impl = sys.implementation
print("MicroPython", impl.version, "on", sys.platform)
mpy = getattr(impl, "_mpy", None)
if mpy is not None:
    print(".mpy format v%d.%d  (mpy-cross must emit this version)" % (mpy & 0xFF, (mpy >> 8) & 3))
total = gc.mem_free() + gc.mem_alloc()
print("heap size %d bytes" % total)
f0 = line("at start")

# 1. importing (= compiling .py on the mouse unless a .mpy is present)
for name in ("maze_logic", "motion", "mission"):
    t0 = time.ticks_ms()
    try:
        __import__(name)
        f1 = line("after import %s (%d ms)" % (name, time.ticks_diff(time.ticks_ms(), t0)), f0)
        f0 = f1
    except MemoryError:
        print("!! MemoryError while importing", name, "-> use .mpy files")
    except ImportError as e:
        print("!! could not import", name, ":", e)

# 2. maze map size and planning speed
try:
    from maze_logic import MazeMap, OPEN
    for rows, cols in ((4, 6), (8, 8), (16, 16)):
        before = free()
        m = MazeMap(rows, cols)
        for y in range(rows):                    # open every interior wall:
            for x in range(cols):                # worst case for BFS
                for d in range(4):
                    m.set_wall(x, y, d, OPEN)
        after = free()
        t0 = time.ticks_ms()
        m.bfs((0, 0), lambda x, y: False)        # unreachable goal = visit all
        t_bfs = time.ticks_diff(time.ticks_ms(), t0)
        t0 = time.ticks_ms()
        m.room_candidates()
        t_room = time.ticks_diff(time.ticks_ms(), t0)
        print("%2dx%-2d map %6d bytes | full BFS %4d ms | room scan %4d ms"
              % (rows, cols, before - after, t_bfs, t_room))
        del m
except MemoryError:
    print("!! MemoryError building/planning the map")

# 3. real control-loop period (motors OFF)
try:
    import uct_mouse
    import motion
    uct_mouse.init()
    uct_mouse.set_motors(0, 0)
    mo = motion.Motion()
    mo.dt_sum = 0.0
    n = 200
    worst = 0
    t_prev = time.ticks_us()
    for _ in range(n):
        mo.tick(0, 0)
        t = time.ticks_us()
        worst = max(worst, time.ticks_diff(t, t_prev))
        t_prev = t
    avg_ms = mo.dt_sum / n * 1000
    print("control loop: average %.2f ms, worst %.2f ms (10 ms is the ideal)"
          % (avg_ms, worst / 1000))
    if avg_ms > 0:
        print("  -> a fixed 0.01 s would under-count gyro turns by %.1f%%"
              % ((1 - 10.0 / avg_ms) * 100))
    uct_mouse.set_motors(0, 0)
except MemoryError:
    print("!! MemoryError during the loop test")

line("at end")
print("done")
