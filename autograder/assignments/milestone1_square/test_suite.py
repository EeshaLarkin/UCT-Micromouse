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

    if max_displacement < 0.20:
        score = 0.0
        feedback.append("GRADE: 0% - Mouse did not complete the square run or fail to move.")
        return score, "\n".join(feedback)

    # Continuous Grading Curve:
    # - Error <= 5cm           -> 100%
    # - Error between 5-15cm   -> Tapers from 100% down to 85%
    # - Error between 15-30cm  -> Tapers from 85% down to 60% (baseline pass)
    # - Error > 30cm           -> Tapers from 60% down to 0% at 1.0m
    if d_e <= 0.05:
        grade = 100.0
    elif d_e <= 0.15:
        grade = 100.0 - (100.0 - 85.0) * (d_e - 0.05) / (0.15 - 0.05)
    elif d_e <= 0.30:
        grade = 85.0 - (85.0 - 60.0) * (d_e - 0.15) / (0.30 - 0.15)
    else:
        grade = max(0.0, 60.0 - 60.0 * (d_e - 0.30) / (1.00 - 0.30))

    feedback.append(f"Base accuracy score: {grade:.2f}%")

    # Penalties
    penalty = 0.0
    if crashed:
        penalty += 15.0
        feedback.append("[Evaluation] Applied collision penalty: -15%")
    
    # Timeout threshold: we allow a tiny floating-point margin (e.g. 0.05s)
    if sim_time >= TIME_LIMIT:
        penalty += 10.0
        feedback.append("[Evaluation] Applied timeout penalty: -10%")

    final_grade = max(0.0, grade - penalty)
    final_grade_rounded = round(final_grade)
    feedback.append(f"GRADE: {final_grade_rounded}%")

    return float(final_grade_rounded), "\n".join(feedback)
