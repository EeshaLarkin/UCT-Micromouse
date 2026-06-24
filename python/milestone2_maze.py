# =========================================================================
# UCT Micromouse - Milestone 2: Map and Navigate a Maze
# =========================================================================

import uct_mouse
import math
import time

# Constants
MAZE_DIM = 10
CELL_LENGTH_M = 0.20
TICK_DIST_M = (2.0 * math.pi * 0.031) / 8.0

# Directions: 0: North, 1: East, 2: South, 3: West
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]

class MazeSolver:
    def __init__(self):
        # 0 = unknown, 1 = wall, 2 = open
        self.walls = [[ [0]*4 for _ in range(MAZE_DIM)] for _ in range(MAZE_DIM)]
        self.visited = [[False]*MAZE_DIM for _ in range(MAZE_DIM)]
        self.x = 0
        self.y = 0
        self.dir = 1
        self.heading_deg = 0.0
        
        # Border walls
        for i in range(MAZE_DIM):
            self.walls[i][0][3] = 1 # West border
            self.walls[i][MAZE_DIM-1][1] = 1 # East border
            self.walls[0][i][2] = 1 # South border
            self.walls[MAZE_DIM-1][i][0] = 1 # North border
            
    def _read_sensors(self):
        tof_l, tof_c, tof_r = uct_mouse.get_tof()
        lenc, renc = uct_mouse.get_encoders()
        sensors = uct_mouse._mouse.get_sensors()
        gyro = sensors.get('gyro', 0.0)
        return tof_l, tof_c, tof_r, lenc, renc, gyro

    def _update_walls(self, tof_l, tof_c, tof_r):
        self.visited[self.y][self.x] = True
        
        front_dir = self.dir
        if tof_c < 150:
            self._set_wall(self.x, self.y, front_dir, 1)
        else:
            self._set_wall(self.x, self.y, front_dir, 2)
            
        left_dir = (self.dir - 1) % 4
        if tof_l < 150:
            self._set_wall(self.x, self.y, left_dir, 1)
        else:
            self._set_wall(self.x, self.y, left_dir, 2)
            
        right_dir = (self.dir + 1) % 4
        if tof_r < 150:
            self._set_wall(self.x, self.y, right_dir, 1)
        else:
            self._set_wall(self.x, self.y, right_dir, 2)

    def _set_wall(self, x, y, direction, status):
        self.walls[y][x][direction] = status
        nx = x + DX[direction]
        ny = y + DY[direction]
        if 0 <= nx < MAZE_DIM and 0 <= ny < MAZE_DIM:
            self.walls[ny][nx][(direction + 2) % 4] = status

    def turn_to(self, target_dir):
        if self.dir == target_dir: return
        
        diff_dir = (target_dir - self.dir) % 4
        if diff_dir == 3: diff_dir = -1
        
        target_heading = self.heading_deg - diff_dir * 90.0
        
        while True:
            _, _, _, _, _, gyro = self._read_sensors()
            self.heading_deg += gyro * 0.01
            
            diff = target_heading - self.heading_deg
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            
            if abs(diff) < 5.0:
                break
                
            pwm = 50
            if abs(diff) < 25: pwm = 25
            
            if diff > 0:
                uct_mouse.set_motors(-pwm, pwm)
            else:
                uct_mouse.set_motors(pwm, -pwm)
                
            uct_mouse.delay_ms(10)
            
        uct_mouse.set_motors(0, 0)
        uct_mouse.delay_ms(50)
        self.dir = target_dir

    def align_to_walls(self):
        # Fine-tune position if there's a wall in front
        for _ in range(8): # Max 8 steps of alignment
            tof_l, tof_c, tof_r, _, _, gyro = self._read_sensors()
            self.heading_deg += gyro * 0.01
            
            if tof_c < 120: # There is a wall in front we can align to
                error = tof_c - 60.0 # 60mm is perfectly centered
                if abs(error) < 10.0:
                    break
                pwm = max(15, min(40, abs(error) * 2.0))
                if error > 0:
                    uct_mouse.set_motors(pwm, pwm)
                else:
                    uct_mouse.set_motors(-pwm, -pwm)
                uct_mouse.delay_ms(10)
            else:
                break
        uct_mouse.set_motors(0, 0)
        uct_mouse.delay_ms(30)

    def move_forward(self):
        target_heading = self.heading_deg
        lenc_start, renc_start = uct_mouse.get_encoders()
        # Compensate for 2% slip
        target_dist = 0.20 / (1.0 - 0.02)
        
        while True:
            _, _, _, lenc, renc, gyro = self._read_sensors()
            self.heading_deg += gyro * 0.01
            
            dist = ((lenc - lenc_start) + (renc - renc_start)) / 2.0 * TICK_DIST_M
            error = target_dist - dist
            
            if error < 0.008: # within 8mm
                break
                
            speed = max(20, min(80, error * 350))
            
            diff = target_heading - self.heading_deg
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            
            corr = diff * 2.5
            
            # Wall centering
            tof_l, _, tof_r, _, _, _ = self._read_sensors()
            wall_corr = 0.0
            if tof_l < 120 and tof_r < 120:
                wall_corr = (tof_l - tof_r) * 0.05
            elif tof_l < 120:
                wall_corr = (tof_l - 80.0) * 0.1
            elif tof_r < 120:
                wall_corr = (80.0 - tof_r) * 0.1
                
            corr += wall_corr
            
            l_pwm = speed - corr
            r_pwm = speed + corr
            uct_mouse.set_motors(max(-40, min(90, l_pwm)), max(-40, min(90, r_pwm)))
            uct_mouse.delay_ms(10)

        # Active brake
        uct_mouse.set_motors(-40, -40)
        uct_mouse.delay_ms(30)
        uct_mouse.set_motors(0, 0)
        uct_mouse.delay_ms(50)
        
        self.align_to_walls()
        
        self.x += DX[self.dir]
        self.y += DY[self.dir]

    def find_nearest_unvisited(self):
        queue = [(self.x, self.y)]
        visited_bfs = [[False]*MAZE_DIM for _ in range(MAZE_DIM)]
        visited_bfs[self.y][self.x] = True
        parent = {}
        
        while queue:
            cx, cy = queue.pop(0)
            if not self.visited[cy][cx]:
                path = []
                curr = (cx, cy)
                while curr != (self.x, self.y):
                    path.append(curr)
                    curr = parent[curr]
                path.reverse()
                return path
                
            for d in range(4):
                if self.walls[cy][cx][d] != 1:
                    nx = cx + DX[d]
                    ny = cy + DY[d]
                    if 0 <= nx < MAZE_DIM and 0 <= ny < MAZE_DIM and not visited_bfs[ny][nx]:
                        visited_bfs[ny][nx] = True
                        parent[(nx, ny)] = (cx, cy)
                        queue.append((nx, ny))
        return None

    def find_path_to_center(self):
        queue = [(self.x, self.y)]
        visited_bfs = [[False]*MAZE_DIM for _ in range(MAZE_DIM)]
        visited_bfs[self.y][self.x] = True
        parent = {}
        target_found = None
        
        while queue:
            cx, cy = queue.pop(0)
            if cx in [4, 5] and cy in [4, 5]:
                target_found = (cx, cy)
                break
                
            for d in range(4):
                if self.walls[cy][cx][d] != 1:
                    nx = cx + DX[d]
                    ny = cy + DY[d]
                    if 0 <= nx < MAZE_DIM and 0 <= ny < MAZE_DIM and not visited_bfs[ny][nx]:
                        visited_bfs[ny][nx] = True
                        parent[(nx, ny)] = (cx, cy)
                        queue.append((nx, ny))
                        
        if not target_found:
            return None
            
        path = []
        curr = target_found
        while curr != (self.x, self.y):
            path.append(curr)
            curr = parent[curr]
        path.reverse()
        return path

    def solve(self):
        if not uct_mouse.init():
            return

        try:
            with open("polarity.txt", "r") as f:
                lines = f.read().strip().split(",")
                uct_mouse.set_polarity(int(lines[0]), int(lines[1]))
        except Exception:
            uct_mouse.set_polarity(1, 1)

        print("--- Milestone 2: 100% Maze Exploration ---")
        
        for _ in range(5):
            uct_mouse.delay_ms(50)

        while True:
            tof_l, tof_c, tof_r, _, _, _ = self._read_sensors()
            self._update_walls(tof_l, tof_c, tof_r)
            
            path = self.find_nearest_unvisited()
            if not path:
                print("All reachable cells visited!")
                break
                
            next_x, next_y = path[0]
            
            target_dir = 0
            for d in range(4):
                if self.x + DX[d] == next_x and self.y + DY[d] == next_y:
                    target_dir = d
                    break
                    
            self.turn_to(target_dir)
            self.move_forward()

        print("Now navigating to the center.")
        while True:
            if self.x in [4, 5] and self.y in [4, 5]:
                print("Reached the center!")
                break
                
            path = self.find_path_to_center()
            if not path:
                print("Center not reachable!")
                break
                
            next_x, next_y = path[0]
            target_dir = 0
            for d in range(4):
                if self.x + DX[d] == next_x and self.y + DY[d] == next_y:
                    target_dir = d
                    break
            self.turn_to(target_dir)
            self.move_forward()

def main():
    solver = MazeSolver()
    solver.solve()

if __name__ == "__main__":
    main()
