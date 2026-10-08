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

# Calibrated 6-Test Evaluation Suite (25% Public Baseline, 5x15% Hidden Stress Tests)
# Public Test 1 carries 25% weight (15.0/60 pts) and uses original baseline rubric (~87% avg).
# Hidden Tests 2-6 carry 15% weight each (9.0/60 pts each) with continuous linear deductions.
# All physical parameters realistically bounded: Imbalance <= 12%, Slip <= 12%
# format: (name, weight, imbalance, slip, is_hidden)
TEST_RUNS = [
    ("Test 1: Public Baseline Run", 0.25, 0.05, 0.03, False),
    ("Test 2: Hidden Positive Imbalance (+12%)", 0.15, 0.12, 0.06, True),
    ("Test 3: Hidden Negative Imbalance (-12%)", 0.15, -0.12, 0.06, True),
    ("Test 4: Hidden Traction Slip & Spin (12% Slip)", 0.15, 0.06, 0.12, True),
    ("Test 5: Hidden Turn Settling & Dynamic Skid", 0.15, -0.12, 0.10, True),
    ("Test 6: Hidden Compound Perturbation", 0.15, 0.12, 0.12, True)
]

def evaluate_run(trajectory_file, is_hidden=False):
    try:
        with open(trajectory_file, "r") as f:
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

    # Segment the trajectory chronologically into 4 straight legs and 4 turns
    raw_thetas = [pt[2] for pt in trajectory]
    unwrapped = unwrap_angles(raw_thetas)
    
    # Detect turn direction: positive unwrapped change = CCW, negative = CW
    final_angle_change = unwrapped[-1] - unwrapped[0]
    direction_sign = 1.0
    if final_angle_change < -math.pi / 2.0:
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
            if th < math.radians(15.0):
                legs_points[0].append((tx, ty, raw_th))
            else:
                current_state = 1
                turns_points[0].append((tx, ty, raw_th))
        elif current_state == 1:
            if th < math.radians(75.0):
                turns_points[0].append((tx, ty, raw_th))
            else:
                current_state = 2
                legs_points[1].append((tx, ty, raw_th))
        elif current_state == 2:
            if th < math.radians(105.0):
                legs_points[1].append((tx, ty, raw_th))
            else:
                current_state = 3
                turns_points[1].append((tx, ty, raw_th))
        elif current_state == 3:
            if th < math.radians(165.0):
                turns_points[1].append((tx, ty, raw_th))
            else:
                current_state = 4
                legs_points[2].append((tx, ty, raw_th))
        elif current_state == 4:
            if th < math.radians(195.0):
                legs_points[2].append((tx, ty, raw_th))
            else:
                current_state = 5
                turns_points[2].append((tx, ty, raw_th))
        elif current_state == 5:
            if th < math.radians(255.0):
                turns_points[2].append((tx, ty, raw_th))
            else:
                current_state = 6
                legs_points[3].append((tx, ty, raw_th))
        elif current_state == 6:
            if th < math.radians(285.0):
                legs_points[3].append((tx, ty, raw_th))
            else:
                current_state = 7
                turns_points[3].append((tx, ty, raw_th))
        elif current_state == 7:
            if th < math.radians(345.0):
                turns_points[3].append((tx, ty, raw_th))
            else:
                current_state = 8
                turn4_end_heading = raw_th
        elif current_state == 8:
            turn4_end_heading = raw_th

    if turn4_end_heading is None and len(trajectory) > 0:
        if current_state >= 7 or len(turns_points[3]) > 0:
            turn4_end_heading = raw_thetas[-1]

    # Evaluate the 4 Straight Line Segments (30 points total - 7.5 points per leg)
    leg_scores = []
    feedback.append("\n--- Leg Trajectory Analysis (Straightness & Length) ---")
    for i in range(4):
        pts = legs_points[i]
        if len(pts) < 3:
            feedback.append(f"  Leg {i+1}: Insufficient trajectory points. Scored 0.0/7.5")
            leg_scores.append(0.0)
            continue
            
        leg_len = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        len_error = abs(leg_len - 1.0)
        
        if not is_hidden:
            # Public Baseline Run (original submission rubric): full score if error <= 5cm, scales to 0 at 25cm
            if len_error <= 0.05:
                len_score = 3.75
            else:
                len_score = max(0.0, 3.75 - (len_error - 0.05) / 0.20 * 3.75)
        else:
            # Hidden Stress Tests: continuous linear taper from 0cm down to 0 at 15cm
            len_score = max(0.0, 3.75 * (1.0 - len_error / 0.15))
            
        x0, y0 = pts[0][0], pts[0][1]
        x1, y1 = pts[-1][0], pts[-1][1]
        line_len = math.hypot(x1 - x0, y1 - y0)
        
        max_dev = 0.0
        if line_len > 1e-3:
            for pt in pts:
                px, py = pt[0], pt[1]
                dev = abs((y1 - y0) * px - (x1 - x0) * py + x1 * y0 - y1 * x0) / line_len
                max_dev = max(max_dev, dev)
                
        if not is_hidden:
            # Public Baseline Run: full score if max dev <= 2cm, scales to 0 at 15cm
            if max_dev <= 0.02:
                straight_score = 3.75
            else:
                straight_score = max(0.0, 3.75 - (max_dev - 0.02) / 0.13 * 3.75)
        else:
            # Hidden Stress Tests: continuous linear taper from 0cm down to 0 at 10cm
            straight_score = max(0.0, 3.75 * (1.0 - max_dev / 0.10))
            
        leg_score = len_score + straight_score
        leg_scores.append(leg_score)
        feedback.append(f"  Leg {i+1} ({['East', 'North', 'West', 'South'][i]}): Length={leg_len:.2f}m (err={len_error*100:.1f}cm), Max Dev={max_dev*100:.1f}cm -> Score {leg_score:.2f}/7.50")

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

    # Evaluate the 4 Turns / Right-Angleness (30 points total - 7.5 points per corner)
    turn_scores = []
    feedback.append("\n--- Corner Analysis (Right-Angleness) ---")
    for i in range(4):
        if len(legs_points[i]) < 3:
            feedback.append(f"  Corner {i+1}: Incomplete turn trajectory (missing Leg {i+1}). Scored 0.0/7.5")
            turn_scores.append(0.0)
            continue
            
        h_start = leg_headings[i]
        
        if i < 3:
            if len(legs_points[i + 1]) < 3:
                feedback.append(f"  Corner {i+1}: Incomplete turn trajectory (missing Leg {i+2}). Scored 0.0/7.5")
                turn_scores.append(0.0)
                continue
            h_end = leg_headings[i + 1]
        else:
            if turn4_end_heading is not None:
                h_end = turn4_end_heading
            elif turns_points[3]:
                h_end = turns_points[3][-1][2]
            elif len(trajectory) > 0:
                final_theta = trajectory[-1][2]
                h_end = (final_theta + math.pi) % (2.0 * math.pi) - math.pi
            else:
                feedback.append(f"  Corner {i+1}: Incomplete turn trajectory. Scored 0.0/7.5")
                turn_scores.append(0.0)
                continue
        
        turn_angle = (h_end - h_start + math.pi) % (2.0 * math.pi) - math.pi
        turn_deg = abs(math.degrees(turn_angle))
        turn_error = abs(turn_deg - 90.0)
        
        if not is_hidden:
            # Public Baseline Run: full score if error <= 3 deg, scales to 0 at 15 deg
            if turn_error <= 3.0:
                t_score = 7.5
            else:
                t_score = max(0.0, 7.5 - (turn_error - 3.0) / 12.0 * 7.5)
        else:
            # Hidden Stress Tests: continuous linear taper from 0 deg down to 0 at 12 deg
            t_score = max(0.0, 7.50 * (1.0 - turn_error / 12.0))
            
        turn_scores.append(t_score)
        feedback.append(f"  Corner {i+1} ({['E->N', 'N->W', 'W->S', 'S->E'][i]}): Turn Angle={turn_deg:.1f}° (err={turn_error:.1f}°) -> Score {t_score:.2f}/7.50")

    # Return & Parking accuracy (20 points)
    feedback.append("\n--- Return & Parking Accuracy ---")
    candidate_points = []
    if len(legs_points[3]) > 0:
        candidate_points.extend(legs_points[3][max(0, len(legs_points[3]) - 5):])
    if len(turns_points[3]) > 0:
        candidate_points.extend(turns_points[3])
    if len(trajectory) > 0:
        candidate_points.append(trajectory[-1])
        
    if candidate_points:
        d_e = min(math.hypot(p[0] - start_x, p[1] - start_y) for p in candidate_points)
    else:
        d_e = math.hypot(final_x - start_x, final_y - start_y)

    if not is_hidden:
        # Public Baseline Run: full score if error <= 3cm, scales to 0 at 25cm
        if d_e <= 0.03:
            parking_score = 20.0
        else:
            parking_score = max(0.0, 20.0 - (d_e - 0.03) / 0.22 * 20.0)
    else:
        # Hidden Stress Tests: continuous linear taper from 0cm down to 0 at 15cm
        parking_score = max(0.0, 20.0 * (1.0 - d_e / 0.15))
        
    feedback.append(f"  Return Offset (at Square Completion): {d_e*100:.1f} cm -> Parking Score {parking_score:.2f}/20.0")
    if math.hypot(final_x - start_x, final_y - start_y) > d_e + 0.02:
        feedback.append("  [Info] Extra forward rollout / 5th mini-leg beyond origin incurs 0 penalty.")

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
