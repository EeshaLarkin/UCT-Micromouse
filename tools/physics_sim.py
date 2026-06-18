import os
import sys
import math
import time
import json
import socket
import argparse

# Silence Pygame's startup print in stdout
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

# Try importing dependencies, suppressing Objective-C duplicate class warnings on macOS
try:
    stderr_fd = sys.stderr.fileno()
    saved_stderr_fd = os.dup(stderr_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, stderr_fd)
    try:
        import numpy as np
        import pygame
        import cv2
    finally:
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(devnull_fd)
        os.close(saved_stderr_fd)
except Exception:
    # Fallback to standard import if file descriptor redirection is not supported or fails
    try:
        import numpy as np
        import pygame
        import cv2
    except ImportError:
        print("=========================================================")
        print("ERROR: Missing required Python libraries for simulator.")
        print("Please install them by running:")
        print("  pip install -r python/requirements.txt")
        print("=========================================================")
        sys.exit(1)

# Helper: Line-segment intersection math for ToF ray-casting
def get_intersection(ray_start, ray_dir, line_start, line_end):
    # ray_start = (x, y), ray_dir = (dx, dy)
    # line_start = (x1, y1), line_end = (x2, y2)
    x1, y1 = line_start
    x2, y2 = line_end
    x3, y3 = ray_start
    dx, dy = ray_dir
    
    # Line equation: (1-t)*p1 + t*p2
    # Ray equation: p3 + u*dir
    # Solving for t and u:
    denom = (x1 - x2) * dy - (y1 - y2) * dx
    if abs(denom) < 1e-6:
        return None # Parallel
        
    t = ((x1 - x3) * dy - (y1 - y3) * dx) / denom
    u = ((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0.0 <= t <= 1.0 and u >= 0.0:
        # Intersection point
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (ix, iy, u)
    return None

def generate_random_maze(grid_size=10, block_dim=0.20, seed=None):
    """Generates a randomized DFS-based perfect maze with loops (braid maze layout)."""
    import random
    if seed is not None:
        random.seed(seed)
        
    visited = set()
    stack = []
    
    # Internal walls tracking
    v_walls = set((c, r) for c in range(1, grid_size) for r in range(grid_size))
    h_walls = set((c, r) for c in range(grid_size) for r in range(1, grid_size))
    
    def get_neighbors(cell):
        c, r = cell
        n = []
        if r < grid_size - 1: n.append(('N', (c, r + 1)))
        if r > 0:             n.append(('S', (c, r - 1)))
        if c < grid_size - 1: n.append(('E', (c + 1, r)))
        if c > 0:             n.append(('W', (c - 1, r)))
        return n
        
    curr = (0, 0)
    visited.add(curr)
    
    while len(visited) < grid_size * grid_size:
        neighbors = [nb for nb in get_neighbors(curr) if nb[1] not in visited]
        if neighbors:
            dir_to, next_cell = random.choice(neighbors)
            c, r = curr
            if dir_to == 'N':
                h_walls.remove((c, r + 1))
            elif dir_to == 'S':
                h_walls.remove((c, r))
            elif dir_to == 'E':
                v_walls.remove((c + 1, r))
            elif dir_to == 'W':
                v_walls.remove((c, r))
                
            visited.add(next_cell)
            stack.append(curr)
            curr = next_cell
        elif stack:
            curr = stack.pop()
        else:
            break
            
    # Braid maze: randomly remove 7% of remaining walls to create alternative paths/loops
    v_list = list(v_walls)
    random.shuffle(v_list)
    for w in v_list[:int(len(v_list) * 0.07)]:
        v_walls.remove(w)
        
    h_list = list(h_walls)
    random.shuffle(h_list)
    for w in h_list[:int(len(h_list) * 0.07)]:
        h_walls.remove(w)
        
    segments = []
    for c, r in v_walls:
        segments.append(((c * block_dim, r * block_dim), (c * block_dim, (r + 1) * block_dim)))
    for c, r in h_walls:
        segments.append(((c * block_dim, r * block_dim), ((c + 1) * block_dim, r * block_dim)))
        
    return segments

class PhysicsSimulator:
    def __init__(self, maze_type="empty", imbalance=0.0, slip=0.0, headless=False, seed=None):
        self.maze_type = maze_type
        self.imbalance = imbalance
        self.slip_coeff = slip
        self.headless = headless
        self.seed = seed
        
        # Robot physical parameters (matching simstruct)
        self.L = 0.060  # axle half-length (m)
        self.R = 0.031  # wheel radius (m)
        self.ticks_per_rot = 8.0
        self.max_speed = 0.40  # max wheel speed at 100% PWM (m/s)
        self.tau = 0.15  # motor mechanical time constant (s)
        
        # Sensor pose offsets from robot center (x, y, theta_offset)
        self.sensor_offsets = [
            (0.045, 0.02, math.pi/2),   # Left ToF
            (0.055, 0.0, 0.0),          # Center ToF
            (0.045, -0.02, -math.pi/2)  # Right ToF
        ]
        
        # State: x, y, theta, actual wheel speeds, encoders
        self.reset_state()
        
        # Load Maze Walls
        self.walls = []
        self.build_maze()
        
    def reset_state(self):
        # Starting position: centre of the inner corridor area.
        # (0.5, 0.5) gives 0.5 m clearance to all four border walls, which is
        # enough for a 1 m × 1 m square run with margin to spare.
        # A corner start (0.1, 0.1) only left 0.042 m — less than the 0.058 m
        # collision radius — on the return legs.
        self.x = 0.5
        self.y = 0.5
        self.theta = 0.0  # Facing East
        self.v_l = 0.0
        self.v_r = 0.0
        self.omega = 0.0  # angular velocity (rad/s)
        self.enc_l = 0.0
        self.enc_r = 0.0
        self.last_enc_l = 0.0  # tracks last-sent value to compute per-frame delta
        self.last_enc_r = 0.0
        self.time = 0.0
        self.trajectory = [(self.x, self.y)]
        self.last_actuation = [0, 0]
        
    def build_maze(self):
        # 10x10 Grid (block dimension = 0.20m, total = 2.0m x 2.0m)
        self.grid_size = 10
        self.block_dim = 0.20
        self.maze_width = self.grid_size * self.block_dim
        self.maze_height = self.grid_size * self.block_dim
        
        # Outer border walls
        self.walls.append(((0, 0), (self.maze_width, 0))) # Top
        self.walls.append(((0, self.maze_height), (self.maze_width, self.maze_height))) # Bottom
        self.walls.append(((0, 0), (0, self.maze_height))) # Left
        self.walls.append(((self.maze_width, 0), (self.maze_width, self.maze_height))) # Right
        
        if self.maze_type == "spiral":
            # Add some custom internal walls for a simple spiral
            # Each block has size 0.2m. Let's add segments
            # Center spiral partitions
            for i in range(1, 8):
                self.walls.append(((i*0.2, 0.2), (i*0.2, 1.8)))
        elif self.maze_type == "random":
            # Generate and add randomized DFS maze walls
            random_walls = generate_random_maze(self.grid_size, self.block_dim, self.seed)
            self.walls.extend(random_walls)
                
    def step(self, pwm_l, pwm_r, dt):
        self.last_actuation = [pwm_l, pwm_r]
        
        # Calculate target velocities based on PWM and motor imbalance
        gain_l = 1.0 - max(0.0, self.imbalance)
        gain_r = 1.0 - max(0.0, -self.imbalance)
        
        target_v_l = (pwm_l / 100.0) * self.max_speed * gain_l
        target_v_r = (pwm_r / 100.0) * self.max_speed * gain_r
        
        # Motor dynamics (lag)
        self.v_l += (target_v_l - self.v_l) / self.tau * dt
        self.v_r += (target_v_r - self.v_r) / self.tau * dt
        
        # Apply traction wheel slip (reducing effective movement randomly)
        eff_v_l = self.v_l
        eff_v_r = self.v_r
        if self.slip_coeff > 0:
            eff_v_l *= (1.0 - np.random.uniform(0.0, self.slip_coeff))
            eff_v_r *= (1.0 - np.random.uniform(0.0, self.slip_coeff))
            
        # Kinematics
        v = (eff_v_l + eff_v_r) / 2.0
        omega = (eff_v_r - eff_v_l) / (2.0 * self.L)
        self.omega = omega
        
        self.theta += omega * dt
        self.theta = (self.theta + math.pi) % (2.0 * math.pi) - math.pi # Wrap to [-pi, pi]
        
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        
        # Log path
        if not self.trajectory or math.hypot(self.x - self.trajectory[-1][0], self.y - self.trajectory[-1][1]) > 0.01:
            self.trajectory.append((self.x, self.y))
            
        # Integrate Encoders (measures physical rotations, before slip)
        self.enc_l += (self.v_l * dt) / (2.0 * math.pi * self.R) * self.ticks_per_rot
        self.enc_r += (self.v_r * dt) / (2.0 * math.pi * self.R) * self.ticks_per_rot
        
        self.time += dt
        
    def read_gyro(self):
        """Converts angular velocity to degrees/s and injects minor white noise (dps)."""
        gyro_dps = (self.omega * 180.0 / math.pi) + np.random.normal(0.0, 0.05)
        return gyro_dps
        
    def read_tofs(self):
        distances = []
        for ox, oy, otheta in self.sensor_offsets:
            # Position of the sensor in world frame
            s_theta = self.theta + otheta
            s_x = self.x + ox * math.cos(self.theta) - oy * math.sin(self.theta)
            s_y = self.y + ox * math.sin(self.theta) + oy * math.cos(self.theta)
            
            ray_dir = (math.cos(s_theta), math.sin(s_theta))
            min_dist = 2.0  # Max sensor range in meters
            
            for line_start, line_end in self.walls:
                res = get_intersection((s_x, s_y), ray_dir, line_start, line_end)
                if res:
                    min_dist = min(min_dist, res[2])
                    
            # Add minor sensor variance noise (0.01m)
            min_dist += np.random.normal(0, 0.005)
            min_dist = max(0.0, min_dist)
            
            # Convert to integer millimeters
            distances.append(int(min_dist * 1000))
        return distances

    def check_collision(self):
        # Collision check based on approximate mouse radius
        mouse_radius = 0.058 # 5.8cm
        for line_start, line_end in self.walls:
            # Distance from point (x,y) to line segment
            px = line_end[0] - line_start[0]
            py = line_end[1] - line_start[1]
            something = px*px + py*py
            u = ((self.x - line_start[0]) * px + (self.y - line_start[1]) * py) / float(something)
            u = max(0.0, min(1.0, u))
            ix = line_start[0] + u * px
            iy = line_start[1] + u * py
            dist = math.hypot(self.x - ix, self.y - iy)
            if dist < mouse_radius:
                return True
        return False

def main():
    parser = argparse.ArgumentParser(description="UCT Micromouse Python Physics & Graphics Simulator")
    parser.add_argument("--map", choices=["empty", "spiral", "random"], default="empty", help="Select maze layout")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for procedural maze generation")
    parser.add_argument("--imbalance", type=float, default=0.08, help="Motor asymmetry imbalance coefficient (-0.2 to 0.2)")
    parser.add_argument("--slip", type=float, default=0.08, help="Wheel traction slip coefficient (0.0 to 0.3)")
    parser.add_argument("--video", type=str, default="", help="Output path to record MP4 video file")
    parser.add_argument("--headless", action="store_true", help="Run in headless cloud mode (no window display)")
    parser.add_argument("--json-log", type=str, default="", help="Path to save simulation telemetry log as JSON")
    parser.add_argument("--max-time", type=float, default=None, help="Maximum simulation time limit in seconds")
    args = parser.parse_args()
    
    sim = PhysicsSimulator(maze_type=args.map, imbalance=args.imbalance, slip=args.slip, headless=args.headless, seed=args.seed)
    
    # Initialize Pygame in dummy mode if headless
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        
    pygame.init()
    width, height = 600, 600
    if args.headless:
        # Headless rendering uses an offscreen surface
        screen = pygame.Surface((width, height))
    else:
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("UCT Micromouse Co-Simulation Testbed")
        
    clock = pygame.time.Clock()
    
    # Initialize Video Writer if requested
    video_writer = None
    if args.video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(args.video, fourcc, 20.0, (width, height))
        print(f"[Simulator] Video recording enabled. Saving to: {args.video}")
        
    # Start TCP Socket Server
    port = 8000
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", port))
    server_sock.listen(1)
    print(f"[Simulator] Server listening on localhost:{port}")
    print("[Simulator] Waiting for student script to connect...")
    
    try:
        conn, addr = server_sock.accept()
        print(f"[Simulator] Student connected from {addr[0]}:{addr[1]}")
    except KeyboardInterrupt:
        server_sock.close()
        sys.exit(0)
        
    running = True
    crashed = False
    rate_hz = 20 # Default sync rate
    dt = 1.0 / rate_hz
    
    # Main simulation tick loop
    try:
        while running:
            # Handle Pygame events to prevent window hang
            if not args.headless:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        
            # 1. Listen for Actuation target from student script
            try:
                conn.settimeout(0.5)
                rx_bytes = conn.recv(1024)
                if not rx_bytes:
                    break
                rx_str = rx_bytes.decode('utf-8').strip()
                
                # Split and parse lines
                for line in rx_str.split('\n'):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "a" in data: # Actuation target
                            pwm_l, pwm_r = data["a"]
                            # Step simulation physics forward by dt
                            sim.step(pwm_l, pwm_r, dt)
                        elif "p" in data or "c" in data:
                            # Step simulation using last actuation targets to maintain lock-step velocity
                            sim.step(sim.last_actuation[0], sim.last_actuation[1], dt)
                        if "c" in data: # Configuration target
                            cfg = data["c"]
                            if "rate" in cfg:
                                rate_hz = cfg["rate"]
                                dt = 1.0 / rate_hz
                    except json.JSONDecodeError:
                        pass
            except socket.timeout:
                pass # timeout is fine, keeps rendering loop alive
                
            # 2. Collision checking
            if sim.check_collision():
                print("[Simulator] CRASH! Mouse hit a wall.")
                crashed = True
                running = False
                
            # Time limit checking
            if args.max_time and sim.time >= args.max_time:
                print(f"[Simulator] Time Limit Exceeded ({args.max_time}s).")
                running = False
                
            # 3. Draw Simulation Environment
            screen.fill((18, 18, 18)) # Dark theme background
            
            # Draw grid blocks
            scale = width / sim.maze_width
            for i in range(sim.grid_size):
                for j in range(sim.grid_size):
                    rect = pygame.Rect(i*sim.block_dim*scale, j*sim.block_dim*scale, sim.block_dim*scale, sim.block_dim*scale)
                    pygame.draw.rect(screen, (35, 35, 35), rect, 1)
                    
            # Draw trajectory path
            if len(sim.trajectory) > 1:
                pygame_pts = [(pt[0]*scale, (sim.maze_height - pt[1])*scale) for pt in sim.trajectory]
                pygame.draw.lines(screen, (0, 150, 255), False, pygame_pts, 2)
                
            # Draw ToF rays
            tofs = sim.read_tofs()
            for idx, (ox, oy, otheta) in enumerate(sim.sensor_offsets):
                s_theta = sim.theta + otheta
                s_x = sim.x + ox * math.cos(sim.theta) - oy * math.sin(sim.theta)
                s_y = sim.y + ox * math.sin(sim.theta) + oy * math.cos(sim.theta)
                
                # Compute projection length
                dist_m = tofs[idx] / 1000.0
                end_x = s_x + dist_m * math.cos(s_theta)
                end_y = s_y + dist_m * math.sin(s_theta)
                
                pygame.draw.line(screen, (220, 50, 50), 
                                 (s_x*scale, (sim.maze_height - s_y)*scale), 
                                 (end_x*scale, (sim.maze_height - end_y)*scale), 1)
                
            # Draw walls
            for line_start, line_end in sim.walls:
                pygame.draw.line(screen, (240, 240, 240), 
                                 (line_start[0]*scale, (sim.maze_height - line_start[1])*scale), 
                                 (line_end[0]*scale, (sim.maze_height - line_end[1])*scale), 4)
                
            # Draw mouse circle
            mouse_px = int(sim.x * scale)
            mouse_py = int((sim.maze_height - sim.y) * scale)
            pygame.draw.circle(screen, (0, 200, 100), (mouse_px, mouse_py), int(0.058*scale)) # 5.8cm radius
            
            # Draw heading arrow
            head_x = int(mouse_px + 0.058 * scale * math.cos(sim.theta))
            head_y = int(mouse_py - 0.058 * scale * math.sin(sim.theta))
            pygame.draw.line(screen, (255, 255, 255), (mouse_px, mouse_py), (head_x, head_y), 3)
            
            # HUD metrics overlay
            font = pygame.font.Font(None, 24) if pygame.font.get_init() else None
            hud_y = 10
            metrics = [
                f"Time: {sim.time:.2f} s",
                f"Encoder L: {int(sim.enc_l)}",
                f"Encoder R: {int(sim.enc_r)}",
                f"ToF L: {tofs[0]} mm",
                f"ToF C: {tofs[1]} mm",
                f"ToF R: {tofs[2]} mm",
                f"PWM: L={sim.last_actuation[0]} | R={sim.last_actuation[1]}"
            ]
            
            for m_str in metrics:
                if font:
                    text_surface = font.render(m_str, True, (200, 200, 200))
                    screen.blit(text_surface, (10, hud_y))
                    hud_y += 20
                    
            if not args.headless:
                pygame.display.flip()
                clock.tick(20) # Match 20Hz stream rate
                
            # Write frame to video if recording
            if video_writer:
                frame_data = pygame.image.tostring(screen, 'RGB')
                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(height, width, 3)
                video_writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                
            # 4. Stream Telemetry back to student
            gyro_val = sim.read_gyro()
            # Send encoder as true per-frame DELTA (not cumulative total)
            delta_enc_l = int(sim.enc_l) - int(sim.last_enc_l)
            delta_enc_r = int(sim.enc_r) - int(sim.last_enc_r)
            sim.last_enc_l = sim.enc_l
            sim.last_enc_r = sim.enc_r
            tx_str = f'{{"tof_l":{tofs[0]}, "tof_c":{tofs[1]}, "tof_r":{tofs[2]}, "+lenc":{delta_enc_l}, "+renc":{delta_enc_r}, "gyro":{gyro_val:.4f}, "v_batt":6.0}}\r\n'
            try:
                conn.sendall(tx_str.encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                break
                
    except Exception as e:
        print(f"[Simulator] Error encountered: {e}")
    finally:
        # Cleanup
        print("[Simulator] Cleaning up socket connection...")
        try:
            conn.close()
        except NameError:
            pass
        server_sock.close()
        
        if video_writer:
            print("[Simulator] Closing video writer...")
            video_writer.release()
            
        pygame.quit()
        
        # Save JSON log if requested
        if args.json_log:
            try:
                # Calculate metrics
                start_x = sim.trajectory[0][0] if sim.trajectory else 0.0
                start_y = sim.trajectory[0][1] if sim.trajectory else 0.0
                final_x = sim.x
                final_y = sim.y
                
                # Max displacement
                max_displacement = 0.0
                for pt in sim.trajectory:
                    dist = math.hypot(pt[0] - start_x, pt[1] - start_y)
                    if dist > max_displacement:
                        max_displacement = dist
                
                log_data = {
                    "start_x": start_x,
                    "start_y": start_y,
                    "final_x": final_x,
                    "final_y": final_y,
                    "max_displacement": max_displacement,
                    "time": sim.time,
                    "crashed": crashed,
                    "trajectory": sim.trajectory
                }
                with open(args.json_log, "w") as f:
                    json.dump(log_data, f, indent=2)
                print(f"[Simulator] Simulation metrics logged to: {args.json_log}")
            except Exception as ex:
                print(f"[Simulator] Failed to write JSON log: {ex}")
                
        print("[Simulator] Closed successfully.")
        
        if crashed:
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    main()
