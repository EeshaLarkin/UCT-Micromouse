# =========================================================================
# maze_logic.py  -  The "brain" of the Micromouse (no motors, no sensors)
# =========================================================================
# This file only knows about GRID CELLS and WALLS. It never touches
# uct_mouse, so the exact same code runs:
#   * on your laptop in offline_test.py (fake robot, thousands of mazes/sec)
#   * inside the simulator / on the STM32 via main.py (real robot)
#
# Written to be MicroPython-safe: no dataclasses, no typing, no
# collections.deque, no f-strings in hot paths.
#
# ----------------------------- CONVENTIONS -------------------------------
#   Coordinates : (x, y)  x = column (East is +x), y = row (North is +y)
#                 (0, 0) is the start cell in the bottom-left corner.
#   Headings    : 0 = North, 1 = East, 2 = South, 3 = West
#                 (+1 = turn right / clockwise, +3 = turn left)
#   Wall states : UNKNOWN (not seen yet), WALL, OPEN
#   Storage     : walls[y][x][d]  ->  state of the wall on side d of cell (x, y)
# =========================================================================

NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

DX = (0, 1, 0, -1)
DY = (1, 0, -1, 0)
DIR_NAMES = "NESW"

UNKNOWN = 0
WALL = 1
OPEN = 2


def opposite(d):
    return (d + 2) % 4


def left_of(d):
    return (d + 3) % 4


def right_of(d):
    return (d + 1) % 4


class MazeMap:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.walls = [[[UNKNOWN] * 4 for _ in range(cols)] for _ in range(rows)]
        self.visited = [[False] * cols for _ in range(rows)]

        # The outer boundary is always walled - we know this before moving.
        for y in range(rows):
            self.walls[y][0][WEST] = WALL
            self.walls[y][cols - 1][EAST] = WALL
        for x in range(cols):
            self.walls[0][x][SOUTH] = WALL
            self.walls[rows - 1][x][NORTH] = WALL

    # ------------------------------------------------------------------
    # Basic wall access
    # ------------------------------------------------------------------
    def in_bounds(self, x, y):
        return 0 <= x < self.cols and 0 <= y < self.rows

    def get_wall(self, x, y, d):
        return self.walls[y][x][d]

    def set_wall(self, x, y, d, state):
        """Set one wall AND its mirror image in the neighbouring cell.

        A wall is physically shared by two cells: the East wall of (2,1)
        is the West wall of (3,1). If we only updated one side, the planner
        would think it could drive (3,1) -> (2,1) through a solid wall.
        """
        nx = x + DX[d]
        ny = y + DY[d]
        if not self.in_bounds(nx, ny):
            # Outer boundary: never let a noisy reading "open" it.
            return
        self.walls[y][x][d] = state
        self.walls[ny][nx][opposite(d)] = state

    def is_open(self, x, y, d):
        return self.walls[y][x][d] == OPEN

    # ------------------------------------------------------------------
    # Perception -> map
    # ------------------------------------------------------------------
    def record_cell(self, x, y, heading, left_wall, front_wall, right_wall):
        """Store what the three ToF sensors saw while standing in (x, y).

        The sensors are RELATIVE to the robot (left/front/right), but the
        map is ABSOLUTE (N/E/S/W). Converting is just modular arithmetic:
            front = heading, left = heading - 1, right = heading + 1  (mod 4)
        e.g. facing East (1): left = North (0), right = South (2).
        The wall behind us needs no sensor: we just drove through it.
        """
        self.visited[y][x] = True
        self.set_wall(x, y, left_of(heading), WALL if left_wall else OPEN)
        self.set_wall(x, y, heading, WALL if front_wall else OPEN)
        self.set_wall(x, y, right_of(heading), WALL if right_wall else OPEN)

    # ------------------------------------------------------------------
    # Breadth-first search (the core of every planner below)
    # ------------------------------------------------------------------
    def bfs(self, start, is_goal, prefer_dir=None):
        """Shortest path (fewest cells) from start to the first cell where
        is_goal(x, y) is True, travelling ONLY through walls known to be OPEN.

        Returns a list of cells [start, ..., goal], or None if unreachable.

        How it works: a queue holds cells in order of distance from start.
        We pop the closest one, and push each unseen neighbour we can drive
        to, remembering where we came from (parent). Because cells come out
        in distance order, the first goal we pop is guaranteed to be the
        nearest one. Then we walk the parent links backwards to get the path.

        prefer_dir: neighbours are tried starting with this heading, so when
        two cells are equally close the one straight ahead wins (fewer turns).
        """
        sx, sy = start
        parent = [[None] * self.cols for _ in range(self.rows)]
        parent[sy][sx] = start

        if prefer_dir is None:
            order = (NORTH, EAST, SOUTH, WEST)
        else:
            order = (prefer_dir, left_of(prefer_dir), right_of(prefer_dir), opposite(prefer_dir))

        queue = [start]   # plain list + head index = a queue (MicroPython-safe)
        head = 0
        while head < len(queue):
            x, y = queue[head]
            head += 1
            if is_goal(x, y):
                return self._build_path(parent, start, (x, y))
            for d in order:
                if self.walls[y][x][d] != OPEN:
                    continue
                nx = x + DX[d]
                ny = y + DY[d]
                if parent[ny][nx] is None:
                    parent[ny][nx] = (x, y)
                    queue.append((nx, ny))
        return None

    def _build_path(self, parent, start, goal):
        path = [goal]
        cell = goal
        while cell != start:
            cell = parent[cell[1]][cell[0]]
            path.append(cell)
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Planners built on BFS
    # ------------------------------------------------------------------
    def path_to_nearest_unvisited(self, x, y, heading=None):
        """Exploration ('frontier') step: route to the closest cell we have
        not stood in yet. None means everything reachable is explored."""
        visited = self.visited
        return self.bfs((x, y), lambda cx, cy: not visited[cy][cx], heading)

    def shortest_path(self, start, goal_cells, heading=None):
        """Shortest known route from start to ANY cell in goal_cells."""
        goals = set(goal_cells)
        return self.bfs(start, lambda cx, cy: (cx, cy) in goals, heading)

    # ------------------------------------------------------------------
    # 2x2 target room detection
    # ------------------------------------------------------------------
    def room_interior_walls(self, x, y):
        """The 4 internal walls of the 2x2 block whose bottom-left is (x, y).

            +-------+-------+
            | (x,y+1) [D] (x+1,y+1)
            +--[B]--+--[C]--+
            | (x,y)  [A] (x+1,y)
            +-------+-------+
        A = East of (x,y)     B = North of (x,y)
        C = North of (x+1,y)  D = East of (x,y+1)
        """
        return ((x, y, EAST), (x, y, NORTH), (x + 1, y, NORTH), (x, y + 1, EAST))

    def room_perimeter_walls(self, x, y):
        """The 8 outer wall segments around the 2x2 block (2 per side)."""
        return ((x, y, SOUTH), (x + 1, y, SOUTH),
                (x + 1, y, EAST), (x + 1, y + 1, EAST),
                (x, y + 1, NORTH), (x + 1, y + 1, NORTH),
                (x, y, WEST), (x, y + 1, WEST))

    def room_cells(self, x, y):
        return ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))

    def room_candidates(self):
        """Every 2x2 block whose 4 interior walls are all CONFIRMED open.
        UNKNOWN does not count as open: a C-shaped corridor has 3 open
        interior walls and a solid 4th, so guessing gives false alarms.

        Returns a list of (x, y, openings, unknowns) where openings/unknowns
        count the block's 8 perimeter walls known OPEN / not yet seen."""
        found = []
        for y in range(self.rows - 1):
            for x in range(self.cols - 1):
                ok = True
                for cx, cy, d in self.room_interior_walls(x, y):
                    if self.walls[cy][cx][d] != OPEN:
                        ok = False
                        break
                if not ok:
                    continue
                openings = 0
                unknowns = 0
                for cx, cy, d in self.room_perimeter_walls(x, y):
                    s = self.walls[cy][cx][d]
                    if s == OPEN:
                        openings += 1
                    elif s == UNKNOWN:
                        unknowns += 1
                found.append((x, y, openings, unknowns))
        return found

    def find_target_room(self, final=False):
        """Bottom-left (x, y) of the target room, or None if not sure yet.

        Why not accept the first open 2x2 block? On 8x8 arenas the generator
        randomly removes ~7% of walls ('braiding'), which creates FAKE open
        2x2 blocks in about half of all mazes. The REAL room is carved into
        exactly once and its edges are never braided, so it has exactly ONE
        opening in its 8 perimeter walls; fakes nearly always have 2+.

          final=False (while exploring): only accept a block whose perimeter
                      is fully known with exactly 1 opening.
          final=True  (nothing left to explore): accept the best candidate
                      (fewest openings) - covers a hand-built lab maze whose
                      room happens to have two doors.
        """
        cands = self.room_candidates()
        for x, y, openings, unknowns in cands:
            if openings == 1 and unknowns == 0:
                return (x, y)
        if final and cands:
            best = cands[0]
            for c in cands:
                if c[2] < best[2]:
                    best = c
            return (best[0], best[1])
        return None

    def in_room(self, x, y, room):
        rx, ry = room
        return rx <= x <= rx + 1 and ry <= y <= ry + 1

    # ------------------------------------------------------------------
    # Path -> driving instructions
    # ------------------------------------------------------------------
    @staticmethod
    def path_to_headings(path):
        """[(0,0), (1,0), (1,1)] -> [EAST, NORTH]: the heading of each step."""
        headings = []
        for i in range(1, len(path)):
            dx = path[i][0] - path[i - 1][0]
            dy = path[i][1] - path[i - 1][1]
            for d in range(4):
                if DX[d] == dx and DY[d] == dy:
                    headings.append(d)
                    break
        return headings

    @staticmethod
    def compress(headings):
        """Merge repeated headings into straight segments for the sprint:
        [E, E, E, N, N] -> [(E, 3), (N, 2)]  =  'drive 0.6 m, turn, drive 0.4 m'."""
        segments = []
        for d in headings:
            if segments and segments[-1][0] == d:
                segments[-1] = (d, segments[-1][1] + 1)
            else:
                segments.append((d, 1))
        return segments
