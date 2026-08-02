import json
import math

# Milestone 2 parameters: Navigate a random perfect maze to the center
MAP = "random"
TIME_LIMIT = 90.0
IMBALANCE = 0.08
SLIP = 0.02
SEED = 42

def evaluate_run(trajectory_file):
    try:
        with open(trajectory_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        return 0.0, f"Error reading trajectory file: {e}"

    start_x = data.get("start_x", 0.10)
    start_y = data.get("start_y", 0.10)
    final_x = data.get("final_x", start_x)
    final_y = data.get("final_y", start_y)
    sim_time = data.get("time", 0.0)
    crashed = data.get("crashed", False)

    # Center of the 10x10 grid maze (each cell is 0.2m x 0.2m)
    # The center is in cells (4,4), (4,5), (5,4), (5,5) which span x/y in [0.8m, 1.2m]
    target_x = 1.0
    target_y = 1.0
    
    trajectory = data.get("trajectory", [])
    
    # Target center coordinates
    target_x = 1.0
    target_y = 1.0
    
    start_dist = math.hypot(start_x - target_x, start_y - target_y)
    
    # Track closest distance achieved to the center during the run
    if trajectory:
        min_dist_to_center = min([math.hypot(pt[0] - target_x, pt[1] - target_y) for pt in trajectory])
    else:
        min_dist_to_center = math.hypot(final_x - target_x, final_y - target_y)
        
    feedback = []
    feedback.append("=== Milestone 2 Evaluation Results ===")
    feedback.append(f"Start Position      : ({start_x:.4f}, {start_y:.4f})")
    feedback.append(f"Final Position      : ({final_x:.4f}, {final_y:.4f})")
    feedback.append(f"Min Dist to Center  : {min_dist_to_center:.4f} m")
    feedback.append(f"Simulation Time     : {sim_time:.2f} s")
    
    # Reaching target threshold (within 0.25 meters of the maze center point (1.0, 1.0))
    success_threshold = 0.25
    reached = (min_dist_to_center <= success_threshold)
    
    if reached:
        exploration_score = 80.0
        feedback.append("SUCCESS: Mouse successfully reached the center of the maze!")
    else:
        # Progress score based on proximity to center
        exploration_score = 80.0 * max(0.0, 1.0 - min_dist_to_center / start_dist)
        feedback.append("FAILED: Mouse did not reach the center of the maze.")

    # Speed run traversal bonus (up to 20 points) if they successfully reached the center
    speed_bonus = 0.0
    if reached and not crashed:
        if sim_time <= 30.0:
            speed_bonus = 20.0
        elif sim_time <= 90.0:
            speed_bonus = 20.0 - (20.0 - 5.0) * (sim_time - 30.0) / (90.0 - 30.0)
        else:
            speed_bonus = 0.0

    base_grade = exploration_score + speed_bonus

    # Penalties
    timeout_penalty = 10.0 if sim_time >= TIME_LIMIT else 0.0
    if crashed:
        feedback.append("[Evaluation] Collision detected! Simulation halted early.")

    raw_grade = max(0.0, base_grade - timeout_penalty)
    final_grade_rounded = round(raw_grade)

    feedback.append("\n=== Score Arithmetic Breakdown ===")
    feedback.append(f"  Exploration Progress Score  : {exploration_score:5.1f} / 80.0 pts")
    feedback.append(f"  Speed Run Traversal Bonus   : {speed_bonus:5.1f} / 20.0 pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Base Subtotal               : {base_grade:5.1f} / 100.0 pts")
    feedback.append(f"  Timeout Penalty             : -{timeout_penalty:4.1f} pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Raw Calculated Grade        : {raw_grade:5.1f} / 100.0 pts")
    feedback.append(f"  GRADE: {final_grade_rounded}%")

    return float(final_grade_rounded), "\n".join(feedback)
