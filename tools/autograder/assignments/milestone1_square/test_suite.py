import json
import math

def unwrap_angles(thetas):
    if not thetas:
        return []
    res = [thetas[0]]
    for t in thetas[1:]:
        diff = t - res[-1]
        diff = (diff + math.pi) % (2.0 * math.pi) - math.pi
        res.append(res[-1] + diff)
    return res

# Milestone 1 parameters
MAP = "empty"
TIME_LIMIT = 45.0
SEED = 42

# Define multiple evaluation test runs
# format: (name, weight, imbalance, slip, is_hidden)
TEST_RUNS = [
    ("Test 1: Public Baseline Run", 0.25, 0.05, 0.03, False),
    ("Test 2: Hidden Positive Motor Imbalance", 0.15, 0.12, 0.04, True),
    ("Test 3: Hidden Negative Motor Imbalance", 0.15, -0.12, 0.04, True),
    ("Test 4: Hidden High Traction Slip & Spin", 0.15, 0.06, 0.10, True),
    ("Test 5: Hidden Turn Settling & Dynamic Skid", 0.15, -0.12, 0.08, True),
    ("Test 6: Hidden Compound Cross-Axis Perturbation", 0.15, 0.14, 0.10, True)
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
    final_theta = data.get("final_theta", trajectory[-1][2] if trajectory else 0.0)

    feedback = []
    feedback.append("=== Milestone 1 Trajectory Profile Evaluation ===")
    feedback.append(f"Simulation Time  : {sim_time:.2f} s")
    feedback.append(f"Collision State  : {'CRASHED' if crashed else 'CLEAN RUN'}")
    
    if len(trajectory) < 10:
        return 0.0, "Trajectory data incomplete or too short to analyze."

    # Segment the trajectory chronologically into 4 straight legs and 4 turns
    # Uses unwrapped continuous heading to eliminate [pi, -pi] wraparound ambiguity during Turn 4
    raw_thetas = [pt[2] for pt in trajectory]
    unwrapped = unwrap_angles(raw_thetas)
    
    # Detect turn direction: positive unwrapped change = CCW, negative = CW
    max_pos = max(unwrapped) - unwrapped[0]
    max_neg = unwrapped[0] - min(unwrapped)
    final_angle_change = unwrapped[-1] - unwrapped[0]
    
    direction_sign = 1.0
    if max_neg > max_pos + math.radians(20.0) or final_angle_change < -math.pi / 2.0:
        direction_sign = -1.0
        
    angles = [(th - unwrapped[0]) * direction_sign for th in unwrapped]
    
    legs_points = {0: [], 1: [], 2: [], 3: []}
    turns_points = {0: [], 1: [], 2: [], 3: []}
    
    # State tracking: 0=Leg1, 1=Turn1, 2=Leg2, 3=Turn2, 4=Leg3, 5=Turn3, 6=Leg4, 7=Turn4, 8=Finished
    current_state = 0
    turn4_end_heading = None
    
    for idx, pt in enumerate(trajectory):
        tx, ty = pt[0], pt[1]
        th = angles[idx]
        raw_th = raw_thetas[idx]
        
        if current_state == 0:
            # Leg 1: Target heading 0.0 (East)
            if th < math.radians(25.0):
                legs_points[0].append((tx, ty, raw_th))
            else:
                current_state = 1
                turns_points[0].append((tx, ty, raw_th))
        elif current_state == 1:
            # Turn 1: Transitioning East -> North (pi/2)
            if th < math.radians(65.0):
                turns_points[0].append((tx, ty, raw_th))
            else:
                current_state = 2
                legs_points[1].append((tx, ty, raw_th))
        elif current_state == 2:
            # Leg 2: Target heading pi/2 (North)
            if th < math.radians(115.0):
                legs_points[1].append((tx, ty, raw_th))
            else:
                current_state = 3
                turns_points[1].append((tx, ty, raw_th))
        elif current_state == 3:
            # Turn 2: Transitioning North -> West (pi)
            if th < math.radians(155.0):
                turns_points[1].append((tx, ty, raw_th))
            else:
                current_state = 4
                legs_points[2].append((tx, ty, raw_th))
        elif current_state == 4:
            # Leg 3: Target heading pi (West)
            if th < math.radians(205.0):
                legs_points[2].append((tx, ty, raw_th))
            else:
                current_state = 5
                turns_points[2].append((tx, ty, raw_th))
        elif current_state == 5:
            # Turn 3: Transitioning West -> South (3pi/2 or -pi/2)
            if th < math.radians(245.0):
                turns_points[2].append((tx, ty, raw_th))
            else:
                current_state = 6
                legs_points[3].append((tx, ty, raw_th))
        elif current_state == 6:
            # Leg 4: Target heading South
            if th < math.radians(295.0):
                legs_points[3].append((tx, ty, raw_th))
            else:
                current_state = 7
                turns_points[3].append((tx, ty, raw_th))
        elif current_state == 7:
            # Turn 4: Transitioning South -> East (Finish at origin)
            if th < math.radians(335.0):
                turns_points[3].append((tx, ty, raw_th))
            else:
                current_state = 8
                turn4_end_heading = raw_th
        elif current_state == 8:
            turn4_end_heading = raw_th

    # If the run ended during Turn 4 or after stopping without moving forward along a 5th leg,
    # capture the final heading from the last trajectory point.
    if turn4_end_heading is None and len(trajectory) > 0:
        if current_state >= 7 or len(turns_points[3]) > 0:
            turn4_end_heading = raw_thetas[-1]

    # Evaluate the 4 Straight Line Segments (35 points total - 8.75 points per leg)
    leg_scores = []
    feedback.append("\n--- Leg Trajectory Analysis (Straightness & Length) ---")
    for i in range(4):
        pts = legs_points[i]
        if len(pts) < 3:
            feedback.append(f"  Leg {i+1}: Insufficient trajectory points. Scored 0.0/8.75")
            leg_scores.append(0.0)
            continue
            
        # Calculate length (Euclidean distance between start and end of leg)
        leg_len = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        len_error = abs(leg_len - 1.0)
        
        # Score length (out of 4.375 points): full score if error <= 2.5cm, scales to 0 at 12cm
        if len_error <= 0.025:
            len_score = 4.375
        else:
            len_score = max(0.0, 4.375 - (len_error - 0.025) / 0.095 * 4.375)
            
        # Calculate straightness (maximum lateral deviation from ideal straight line vector)
        x0, y0 = pts[0][0], pts[0][1]
        x1, y1 = pts[-1][0], pts[-1][1]
        line_len = math.hypot(x1 - x0, y1 - y0)
        
        max_dev = 0.0
        if line_len > 1e-3:
            for pt in pts:
                px, py = pt[0], pt[1]
                # Perpendicular distance from point (px, py) to line segment (x0,y0)-(x1,y1)
                dev = abs((y1 - y0) * px - (x1 - x0) * py + x1 * y0 - y1 * x0) / line_len
                max_dev = max(max_dev, dev)
                
        # Score straightness (out of 4.375 points): full score if max deviation <= 1.2cm, scales to 0 at 7cm
        if max_dev <= 0.012:
            straight_score = 4.375
        else:
            straight_score = max(0.0, 4.375 - (max_dev - 0.012) / 0.058 * 4.375)
            
        leg_score = len_score + straight_score
        leg_scores.append(leg_score)
        feedback.append(f"  Leg {i+1} ({['East', 'North', 'West', 'South'][i]}): Length={leg_len:.2f}m (err={len_error*100:.1f}cm), Max Dev={max_dev*100:.1f}cm -> Score {leg_score:.2f}/8.75")

    # Calculate representative straight heading for each of the 4 legs (circular mean)
    target_headings = [0.0, math.pi / 2.0, math.pi, -math.pi / 2.0]
    def circular_mean(thetas):
        sin_sum = sum(math.sin(th) for th in thetas)
        cos_sum = sum(math.cos(th) for th in thetas)
        return math.atan2(sin_sum, cos_sum)

    leg_headings = {}
    for i in range(4):
        if len(legs_points[i]) > 0:
            leg_headings[i] = circular_mean([pt[2] for pt in legs_points[i]])
        else:
            leg_headings[i] = target_headings[i]

    # Evaluate the 4 Turns / Right-Angleness (35 points total - 8.75 points per corner)
    turn_scores = []
    feedback.append("\n--- Corner Analysis (Right-Angleness) ---")
    for i in range(4):
        if len(legs_points[i]) < 3:
            feedback.append(f"  Corner {i+1}: Incomplete turn trajectory (missing Leg {i+1}). Scored 0.0/8.75")
            turn_scores.append(0.0)
            continue
            
        h_start = leg_headings[i]
        
        if i < 3:
            if len(legs_points[i + 1]) < 3:
                feedback.append(f"  Corner {i+1}: Incomplete turn trajectory (missing Leg {i+2}). Scored 0.0/8.75")
                turn_scores.append(0.0)
                continue
            h_end = leg_headings[i + 1]
        else:
            # Corner 4: Turn from Leg 4 heading to the final resting heading at the origin
            final_tail = trajectory[-20:] if len(trajectory) >= 20 else trajectory
            resting_heading = circular_mean([pt[2] for pt in final_tail])
            h_end = resting_heading
        
        turn_angle = (h_end - h_start + math.pi) % (2.0 * math.pi) - math.pi
        # Wrap CCW angle to positive degrees
        turn_deg = abs(math.degrees(turn_angle))
        
        # Error from ideal 90 degree turn
        turn_error = abs(turn_deg - 90.0)
        
        # Score (out of 8.75 points): full score if error <= 1.5 degrees, scales to 0 at 6.0 degrees
        if turn_error <= 1.5:
            t_score = 8.75
        else:
            t_score = max(0.0, 8.75 - (turn_error - 1.5) / 4.5 * 8.75)
            
        turn_scores.append(t_score)
        feedback.append(f"  Corner {i+1} ({['E->N', 'N->W', 'W->S', 'S->E'][i]}): Turn Angle={turn_deg:.1f}° (err={turn_error:.1f}°) -> Score {t_score:.2f}/8.75")

    # Return & Parking accuracy (20 points)
    feedback.append("\n--- Return & Parking Accuracy ---")
    
    # Evaluate parking offset across the completion of Leg 4, Turn 4, and final resting position
    # (guarantees students are never penalized for any post-turn creep/motion after the 4th turn)
    candidate_points = [(final_x, final_y), (trajectory[-1][0], trajectory[-1][1])]
    if len(legs_points[3]) > 0:
        candidate_points.append((legs_points[3][-1][0], legs_points[3][-1][1]))
    if len(turns_points[3]) > 0:
        candidate_points.extend([(pt[0], pt[1]) for pt in turns_points[3]])
        
    d_e = min(math.hypot(px - start_x, py - start_y) for px, py in candidate_points)
    
    # Full points if final distance to start is <= 1.8cm, scales to 0 at 8.0cm
    if d_e <= 0.018:
        parking_score = 20.0
    else:
        parking_score = max(0.0, 20.0 - (d_e - 0.018) / 0.062 * 20.0)
    feedback.append(f"  Final Position Offset: {d_e*100:.1f} cm -> Parking Score {parking_score:.2f}/20.0")

    # Efficiency (10 points total - speed cadence)
    feedback.append("\n--- Efficiency & Cadence ---")
    # Speed score: scales from 10 points (time <= 18s) down to 0 points (time >= 32s)
    if sim_time <= 18.0:
        speed_score = 10.0
    else:
        speed_score = max(0.0, 10.0 - (sim_time - 18.0) / 14.0 * 10.0)
        
    feedback.append(f"  Speed Cadence Score (time={sim_time:.1f}s): {speed_score:.2f}/10.0")

    # Final Grade Calculation
    base_legs = sum(leg_scores)
    base_turns = sum(turn_scores)
    total_grade = base_legs + base_turns + parking_score + speed_score
    
    final_grade_rounded = round(total_grade)

    feedback.append("\n=== Score Arithmetic Breakdown ===")
    feedback.append(f"  Leg Segments (Straightness/Length) : {base_legs:5.2f} / 35.00 pts")
    feedback.append(f"  Corner Turn Angles (90 deg accuracy): {base_turns:5.2f} / 35.00 pts")
    feedback.append(f"  Parking Accuracy (return to start) : {parking_score:5.2f} / 20.00 pts")
    feedback.append(f"  Run Speed Efficiency              : {speed_score:5.2f} / 10.00 pts")
    feedback.append(f"  -------------------------------------------")
    feedback.append(f"  Calculated Grade                   : {total_grade:5.2f} / 100.00 pts")
    feedback.append(f"  GRADE: {final_grade_rounded}%")

    return float(final_grade_rounded), "\n".join(feedback)
