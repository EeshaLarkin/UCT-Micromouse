import json
import math

# Milestone 1 parameters
MAP = "empty"
TIME_LIMIT = 45.0
IMBALANCE = 0.08
SLIP = 0.08
SEED = 42

def evaluate_run(trajectory_file):
    try:
        with open(trajectory_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        return 0.0, f"Error reading trajectory file: {e}"

    start_x = data.get("start_x", 0.0)
    start_y = data.get("start_y", 0.0)
    final_x = data.get("final_x", 0.0)
    final_y = data.get("final_y", 0.0)
    max_displacement = data.get("max_displacement", 0.0)
    sim_time = data.get("time", 0.0)
    crashed = data.get("crashed", False)

    # Compute Euclidean error
    d_e = math.hypot(final_x - start_x, final_y - start_y)

    feedback = []
    feedback.append("=== Milestone 1 Evaluation Results ===")
    feedback.append(f"Start position    : ({start_x:.4f}, {start_y:.4f})")
    feedback.append(f"Final position    : ({final_x:.4f}, {final_y:.4f})")
    feedback.append(f"Max Displacement  : {max_displacement:.4f} m")
    feedback.append(f"Final Return Error: {d_e * 100:.2f} cm")
    feedback.append(f"Simulation Time  : {sim_time:.2f} s")

    # Analyze trajectory for square traversal (1.0m sides, clockwise/right turns)
    trajectory = data.get("trajectory", [])
    
    # Define expected corners in sequential order for a right-turning 1.0m square:
    # Corner 1: (start_x + 1.0, start_y)
    # Corner 2: (start_x + 1.0, start_y - 1.0)
    # Corner 3: (start_x, start_y - 1.0)
    expected_corners = [
        (start_x + 1.0, start_y),
        (start_x + 1.0, start_y - 1.0),
        (start_x, start_y - 1.0)
    ]
    
    current_corner_idx = 0
    tolerance = 0.20
    
    for pt in trajectory:
        tx, ty = pt[0], pt[1]
        if current_corner_idx < len(expected_corners):
            cx, cy = expected_corners[current_corner_idx]
            if math.hypot(tx - cx, ty - cy) < tolerance:
                current_corner_idx += 1
                
    # Calculate Grade based on progression corners (20 points per corner visited, up to 60 points)
    progression_score = current_corner_idx * 20.0
    feedback.append(f"[Evaluation] Progression Corners Visited: {current_corner_idx}/3 ({progression_score:.1f} pts)")
    for i in range(current_corner_idx):
        feedback.append(f"  - Reached Corner {i+1} at {expected_corners[i]}")

    return_bonus = 0.0
    accuracy_score = 0.0
    
    # Check if they returned to start to qualify for return bonus and accuracy points
    if current_corner_idx == len(expected_corners):
        # We define a 30cm window as a "reasonable position" relative to starting point
        if d_e <= 0.30:
            return_bonus = 20.0
            feedback.append(f"[Evaluation] Return to start verified within reasonable 30cm limit (+{return_bonus:.1f} pts)")
            
            # Calculate final accuracy score out of remaining 20 points
            if d_e <= 0.05:
                accuracy_score = 20.0
            elif d_e <= 0.15:
                accuracy_score = 20.0 - (20.0 - 10.0) * (d_e - 0.05) / (0.15 - 0.05)
            else:
                accuracy_score = 10.0 - (10.0 - 0.0) * (d_e - 0.15) / (0.30 - 0.15)
            feedback.append(f"  - Return Accuracy Points: {accuracy_score:.2f} / 20.0 pts")
        else:
            feedback.append("[Evaluation] Return to start failed (drift exceeded reasonable 30cm limit). No return/accuracy points awarded.")
    else:
        feedback.append("[Evaluation] Trajectory incomplete. No return/accuracy points awarded.")

    base_grade = progression_score + return_bonus + accuracy_score

    # Penalties
    penalty = 0.0
    timeout_penalty = 0.0
    if crashed:
        feedback.append("[Evaluation] Collision detected! Simulation halted early.")
    if sim_time >= TIME_LIMIT:
        timeout_penalty = 10.0
        penalty += 10.0

    raw_grade = max(0.0, base_grade - penalty)
    final_grade_rounded = round(raw_grade)

    feedback.append("\n=== Score Arithmetic Breakdown ===")
    feedback.append(f"  Progression Score (Corners) : {progression_score:5.1f} / 60.0 pts")
    feedback.append(f"  Controlled Return Bonus     : {return_bonus:5.1f} / 20.0 pts")
    feedback.append(f"  Return Accuracy Points      : {accuracy_score:5.1f} / 20.0 pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Base Subtotal               : {base_grade:5.1f} / 100.0 pts")
    feedback.append(f"  Timeout Penalty             : -{timeout_penalty:4.1f} pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Raw Calculated Grade        : {raw_grade:5.1f} / 100.0 pts")
    feedback.append(f"  GRADE: {final_grade_rounded}%")

    return float(final_grade_rounded), "\n".join(feedback)
