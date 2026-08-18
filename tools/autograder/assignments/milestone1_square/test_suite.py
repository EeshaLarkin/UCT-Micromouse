import json
import math
import numpy as np

# Milestone 1 parameters
MAP = "empty"
TIME_LIMIT = 45.0
SEED = 42

# Define multiple evaluation test runs
# format: (name, weight, imbalance, slip, is_hidden)
TEST_RUNS = [
    ("Test 1: Public Baseline Run", 0.40, 0.05, 0.04, False),
    ("Test 2: Hidden Asymmetry Stress-Test", 0.30, 0.12, 0.02, True),
    ("Test 3: Hidden Starting/Turning Slip Run", 0.30, 0.04, 0.10, True)
]

def evaluate_run(trajectory_file):
    try:
        with open(trajectory_file, "r") as f:
            # Trajectory is stored as a list of dicts or standard summary format
            data = json.load(f)
    except Exception as e:
        return 0.0, f"Error reading trajectory file: {e}"

    start_x = data.get("start_x", 0.0)
    start_y = data.get("start_y", 0.0)
    final_x = data.get("final_x", 0.0)
    final_y = data.get("final_y", 0.0)
    sim_time = data.get("time", 0.0)
    crashed = data.get("crashed", False)
    trajectory = data.get("trajectory", [])

    feedback = []
    feedback.append("=== Milestone 1 Trajectory Profile Evaluation ===")
    feedback.append(f"Simulation Time  : {sim_time:.2f} s")
    feedback.append(f"Collision State  : {'CRASHED' if crashed else 'CLEAN RUN'}")
    
    if len(trajectory) < 10:
        return 0.0, "Trajectory data incomplete or too short to analyze."

    # Segment the trajectory into 4 straight lines and 4 turns based on orientation (theta)
    # The mouse transitions orientation CCW: 0 -> pi/2 (90) -> pi (180) -> -pi/2 (-90) -> 0.
    # We define target headings for the 4 straight legs:
    target_headings = [0.0, math.pi / 2.0, math.pi, -math.pi / 2.0]
    
    # We assign each point in the trajectory to one of the 4 legs or turns
    # We identify which leg the point belongs to by checking the closest target heading.
    legs_points = {0: [], 1: [], 2: [], 3: []}
    turns_points = {0: [], 1: [], 2: [], 3: []}
    
    # We also keep track of orientation transitions to evaluate turn angles
    headings_at_stops = []
    
    # Group points by active path heading
    for pt in trajectory:
        tx, ty, ttheta = pt[0], pt[1], pt[2]
        # Wrap theta to [-pi, pi]
        ttheta = (ttheta + math.pi) % (2.0 * math.pi) - math.pi
        
        # Find which target heading the mouse is closest to
        heading_errors = [abs((ttheta - target + math.pi) % (2.0 * math.pi) - math.pi) for target in target_headings]
        min_err = min(heading_errors)
        closest_leg = heading_errors.index(min_err)
        
        # If the mouse is actively aligned within 25 degrees of a target heading, consider it straight leg
        if min_err < math.radians(25.0):
            legs_points[closest_leg].append((tx, ty, ttheta))
        else:
            # Otherwise, it's turning to the next leg
            # Turn N is the transition from Leg N to Leg (N+1) % 4
            turns_points[closest_leg].append((tx, ty, ttheta))

    # Evaluate the 4 Straight Line Segments (30 points total - 7.5 points per leg)
    leg_scores = []
    feedback.append("\n--- Leg Trajectory Analysis (Straightness & Length) ---")
    for i in range(4):
        pts = legs_points[i]
        if len(pts) < 3:
            feedback.append(f"  Leg {i+1}: Insufficient trajectory points. Scored 0.0/7.5")
            leg_scores.append(0.0)
            continue
            
        # Calculate length (Euclidean distance between start and end of leg)
        leg_len = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        len_error = abs(leg_len - 1.0)
        
        # Score length (out of 3.75 points): full score if error <= 5cm, scales to 0 at 25cm
        if len_error <= 0.05:
            len_score = 3.75
        else:
            len_score = max(0.0, 3.75 - (len_error - 0.05) / 0.20 * 3.75)
            
        # Calculate straightness (maximum lateral deviation from ideal straight line vector)
        p0 = np.array([pts[0][0], pts[0][1]])
        p1 = np.array([pts[-1][0], pts[-1][1]])
        line_vec = p1 - p0
        line_len = np.linalg.norm(line_vec)
        
        max_dev = 0.0
        if line_len > 1e-3:
            for pt in pts:
                p = np.array([pt[0], pt[1]])
                # Perpendicular distance from point p to line segment p0-p1
                dev = np.abs(np.cross(line_vec, p0 - p)) / line_len
                max_dev = max(max_dev, dev)
                
        # Score straightness (out of 3.75 points): full score if max deviation <= 2cm, scales to 0 at 15cm
        if max_dev <= 0.02:
            straight_score = 3.75
        else:
            straight_score = max(0.0, 3.75 - (max_dev - 0.02) / 0.13 * 3.75)
            
        leg_score = len_score + straight_score
        leg_scores.append(leg_score)
        feedback.append(f"  Leg {i+1} ({['East', 'North', 'West', 'South'][i]}): Length={leg_len:.2f}m (err={len_error*100:.1f}cm), Max Dev={max_dev*100:.1f}cm -> Score {leg_score:.2f}/7.50")

    # Evaluate the 4 Turns / Right-Angleness (30 points total - 7.5 points per corner)
    turn_scores = []
    feedback.append("\n--- Corner Analysis (Right-Angleness) ---")
    for i in range(4):
        # We calculate the heading change between Leg i and Leg (i+1)%4
        pts_current = legs_points[i]
        pts_next = legs_points[(i + 1) % 4]
        
        if not pts_current or not pts_next:
            feedback.append(f"  Corner {i+1}: Incomplete turn trajectory. Scored 0.0/7.5")
            turn_scores.append(0.0)
            continue
            
        # Orientation difference
        h_start = pts_current[-1][2]
        h_end = pts_next[0][2]
        
        turn_angle = (h_end - h_start + math.pi) % (2.0 * math.pi) - math.pi
        # Wrap CCW angle to positive degrees
        turn_deg = abs(math.degrees(turn_angle))
        
        # Error from ideal 90 degree turn
        turn_error = abs(turn_deg - 90.0)
        
        # Score (out of 7.5 points): full score if error <= 3 degrees, scales to 0 at 15 degrees
        if turn_error <= 3.0:
            t_score = 7.5
        else:
            t_score = max(0.0, 7.5 - (turn_error - 3.0) / 12.0 * 7.5)
            
        turn_scores.append(t_score)
        feedback.append(f"  Corner {i+1} ({['E->N', 'N->W', 'W->S', 'S->E'][i]}): Turn Angle={turn_deg:.1f}° (err={turn_error:.1f}°) -> Score {t_score:.2f}/7.50")

    # Return & Parking accuracy (20 points)
    feedback.append("\n--- Return & Parking Accuracy ---")
    d_e = math.hypot(final_x - start_x, final_y - start_y)
    # Full points if final distance to start is <= 3cm, scales to 0 at 25cm
    if d_e <= 0.03:
        parking_score = 20.0
    else:
        parking_score = max(0.0, 20.0 - (d_e - 0.03) / 0.22 * 20.0)
    feedback.append(f"  Final Position Offset: {d_e*100:.1f} cm -> Parking Score {parking_score:.2f}/20.0")

    # Efficiency & Safety (20 points total - 10 pts speed, 10 pts safety)
    feedback.append("\n--- Efficiency & Safety ---")
    # Speed score: scales from 10 points (time <= 20s) down to 0 points (time >= 40s)
    if sim_time <= 20.0:
        speed_score = 10.0
    else:
        speed_score = max(0.0, 10.0 - (sim_time - 20.0) / 20.0 * 10.0)
        
    safety_score = 0.0 if crashed else 10.0
    feedback.append(f"  Speed Score (time={sim_time:.1f}s): {speed_score:.2f}/10.0")
    feedback.append(f"  Safety Score (crashed={crashed}): {safety_score:.2f}/10.0")

    # Final Grade Calculation
    base_legs = sum(leg_scores)
    base_turns = sum(turn_scores)
    total_grade = base_legs + base_turns + parking_score + speed_score + safety_score
    
    final_grade_rounded = round(total_grade)

    feedback.append("\n=== Score Arithmetic Breakdown ===")
    feedback.append(f"  Leg Segments (Straightness/Length) : {base_legs:5.2f} / 30.00 pts")
    feedback.append(f"  Corner Turn Angles (90 deg accuracy): {base_turns:5.2f} / 30.00 pts")
    feedback.append(f"  Parking Accuracy (return to start) : {parking_score:5.2f} / 20.00 pts")
    feedback.append(f"  Run Speed Efficiency              : {speed_score:5.2f} / 10.00 pts")
    feedback.append(f"  Safety Bonus (no collision)        : {safety_score:5.2f} / 10.00 pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Calculated Grade                   : {total_grade:5.2f} / 100.00 pts")
    feedback.append(f"  GRADE: {final_grade_rounded}%")

    return float(final_grade_rounded), "\n".join(feedback)
