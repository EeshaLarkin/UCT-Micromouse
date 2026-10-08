#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import json
import signal
import glob
import importlib.util
import math
import shutil
import tempfile

# Force headless environment for SDL/Pygame before any imports
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

# 1. Path Resolution
if os.path.exists("/autograder"):
    SUBMISSION_DIR = "/autograder/submission"
    RESULTS_FILE = "/autograder/results/results.json"
    SOURCE_DIR = "/autograder/source"
    VIDEO_PATH = "/autograder/results/run.mp4"
    TRAJECTORY_JSON = os.path.join(tempfile.gettempdir(), "trajectory.json")
else:
    # Local mock mode
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    SUBMISSION_DIR = os.path.join(base_dir, "python")  # mock submission is the local python dir
    RESULTS_FILE = os.path.join(base_dir, "tools", "autograder", "results.json")
    SOURCE_DIR = os.path.join(base_dir, "tools", "autograder")
    VIDEO_PATH = os.path.join(base_dir, "tools", "autograder", "run.mp4")
    TRAJECTORY_JSON = os.path.join(base_dir, "tools", "autograder", "trajectory.json")

def write_results(score, feedback, test_name="Autograder Evaluation"):
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    scaled_score = round(score / 100.0 * 60.0, 2) if score > 60.0 else round(score, 2)
    results = {
        "score": scaled_score,
        "max_score": 60.0,
        "output": feedback,
        "visibility": "visible",
        "tests": [
            {
                "name": test_name,
                "score": scaled_score,
                "max_score": 60.0,
                "output": feedback,
                "visibility": "visible"
            }
        ]
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[Grader] Results written to {RESULTS_FILE} with score {scaled_score}/60.0")

def generate_trajectory_svg(trajectory_file):
    try:
        if not trajectory_file or not os.path.exists(trajectory_file):
            return ""
        with open(trajectory_file, "r") as f:
            data = json.load(f)
        traj = data.get("trajectory", [])
        if not traj or len(traj) < 2:
            return ""
        
        start_x = data.get("start_x", traj[0][0])
        start_y = data.get("start_y", traj[0][1])
        th0 = traj[0][2]
        
        # Detect turn direction: positive unwrapped change = CCW (+1), negative = CW (-1)
        thetas = [pt[2] for pt in traj]
        unwrapped = []
        if thetas:
            unwrapped = [thetas[0]]
            for t in thetas[1:]:
                diff = t - unwrapped[-1]
                diff = (diff + math.pi) % (2.0 * math.pi) - math.pi
                unwrapped.append(unwrapped[-1] + diff)
                
        dir_sign = 1.0
        if unwrapped:
            max_pos = max(unwrapped) - unwrapped[0]
            max_neg = unwrapped[0] - min(unwrapped)
            final_angle_change = unwrapped[-1] - unwrapped[0]
            if max_neg > max_pos + math.radians(20.0) or final_angle_change < -math.pi / 2.0:
                dir_sign = -1.0
                
        # Ideal square corners: 1m x 1m starting from (start_x, start_y)
        # Unit forward vector: (cos(th0), sin(th0))
        # Unit perpendicular lateral vector: (-dir_sign * sin(th0), dir_sign * cos(th0))
        cos0 = math.cos(th0)
        sin0 = math.sin(th0)
        c0 = (start_x, start_y)
        c1 = (start_x + 1.0 * cos0, start_y + 1.0 * sin0)
        c2 = (start_x + 1.0 * cos0 - dir_sign * 1.0 * sin0, start_y + 1.0 * sin0 + dir_sign * 1.0 * cos0)
        c3 = (start_x - dir_sign * 1.0 * sin0, start_y + dir_sign * 1.0 * cos0)
        c4 = c0
        ideal_pts = [c0, c1, c2, c3, c4]
        
        # Isometric Bounding coordinates (preserves 1:1 aspect ratio)
        all_xs = [pt[0] for pt in traj] + [c[0] for c in ideal_pts]
        all_ys = [pt[1] for pt in traj] + [c[1] for c in ideal_pts]
        raw_min_x, raw_max_x = min(all_xs), max(all_xs)
        raw_min_y, raw_max_y = min(all_ys), max(all_ys)
        
        span = max(raw_max_x - raw_min_x, raw_max_y - raw_min_y, 1.2) + 0.3
        mid_x = (raw_min_x + raw_max_x) / 2.0
        mid_y = (raw_min_y + raw_max_y) / 2.0
        min_x, max_x = mid_x - span / 2.0, mid_x + span / 2.0
        min_y, max_y = mid_y - span / 2.0, mid_y + span / 2.0
        
        w, h = 480, 480
        def to_svg(x, y):
            sx = (x - min_x) / span * (w - 70) + 35
            sy = h - ((y - min_y) / span * (h - 70) + 35)
            return sx, sy
        
        pts = [to_svg(pt[0], pt[1]) for pt in traj]
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        
        ideal_svg_pts = [to_svg(c[0], c[1]) for c in ideal_pts]
        ideal_poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in ideal_svg_pts)
        
        start_sx, start_sy = to_svg(traj[0][0], traj[0][1])
        end_sx, end_sy = to_svg(traj[-1][0], traj[-1][1])
        
        # Avoid label overlap if end marker is parked very close to start
        end_text_y = end_sy + 4.0
        if math.hypot(end_sx - start_sx, end_sy - start_sy) < 25.0:
            end_text_y = end_sy - 10.0
        
        dir_label = "CCW (Left)" if dir_sign > 0 else "CW (Right)"
        
        svg = f'''<div style="margin: 15px 0;">
  <h4 style="margin-bottom: 8px; color: #fff;">📊 Recorded Trajectory Map:</h4>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="background:#181818; border:1px solid #444; border-radius:6px; max-width: 100%; height: auto;">
    <rect width="100%" height="100%" fill="#181818"/>
    <!-- Grid Marks -->
    <line x1="35" y1="15" x2="35" y2="{h-15}" stroke="#2a2a2a" stroke-width="1"/>
    <line x1="15" y1="{h-35}" x2="{w-15}" y2="{h-35}" stroke="#2a2a2a" stroke-width="1"/>
    <!-- Ideal Square Reference -->
    <polyline points="{ideal_poly}" fill="none" stroke="#666666" stroke-width="2" stroke-dasharray="5,5"/>
    <!-- Actual Mouse Trajectory -->
    <polyline points="{polyline}" fill="none" stroke="#00b4d8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- Start & Stop Markers -->
    <circle cx="{start_sx:.1f}" cy="{start_sy:.1f}" r="5" fill="#2ec4b6" stroke="#fff" stroke-width="1.5"/>
    <circle cx="{end_sx:.1f}" cy="{end_sy:.1f}" r="5" fill="#e71d36" stroke="#fff" stroke-width="1.5"/>
    <text x="{start_sx+8:.1f}" y="{start_sy+4:.1f}" fill="#2ec4b6" font-size="11" font-family="sans-serif" font-weight="bold">Start Origin ({traj[0][0]:.2f}, {traj[0][1]:.2f})</text>
    <text x="{end_sx+8:.1f}" y="{end_text_y:.1f}" fill="#e71d36" font-size="11" font-family="sans-serif" font-weight="bold">Stop ({traj[-1][0]:.2f}, {traj[-1][1]:.2f})</text>
    <!-- Legend -->
    <text x="45" y="25" fill="#888888" font-size="10" font-family="sans-serif">--- Ideal Square (1m × 1m, {dir_label})</text>
    <text x="45" y="38" fill="#00b4d8" font-size="10" font-family="sans-serif">── Actual Trajectory</text>
    <text x="45" y="51" fill="#aaaaaa" font-size="9" font-family="sans-serif">Note: Parking is scored at square completion; extra forward rollout is not penalized.</text>
  </svg>
</div>'''
        return svg
    except Exception:
        return ""

def get_video_html(video_path):
    if not video_path or not os.path.exists(video_path):
        return ""
    try:
        # Transcode using ffmpeg to standard H.264 Baseline Profile (YUV420p + faststart)
        # Scaled to 400x400 @ 15fps with CRF 30 to produce lightweight ~100-150KB payload
        # compatible across all browsers (Firefox, Chrome, Safari, Edge) without JSON truncation.
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            opt_video = video_path + ".opt.mp4"
            try:
                cmd = [
                    ffmpeg_bin, "-y", "-nostdin",
                    "-i", video_path,
                    "-vf", "scale=400:400",
                    "-r", "15",
                    "-c:v", "libx264",
                    "-profile:v", "baseline",
                    "-level", "3.0",
                    "-pix_fmt", "yuv420p",
                    "-crf", "30",
                    "-preset", "faster",
                    "-movflags", "+faststart",
                    opt_video
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=20.0, check=True)
                if os.path.exists(opt_video) and os.path.getsize(opt_video) > 0:
                    os.replace(opt_video, video_path)
            except Exception as fe:
                print(f"[Grader] Warning during video transcoding: {fe}")
                if os.path.exists(opt_video):
                    try: os.remove(opt_video)
                    except Exception: pass
                    
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if size_mb > 5.0:  # Cap to prevent Gradescope web UI issues
            return ""
            
        import base64
        with open(video_path, "rb") as vf:
            b64_data = base64.b64encode(vf.read()).decode("utf-8")
            
        return f'''<div style="margin: 15px 0;">
  <h4 style="margin-bottom: 8px; color: #fff;">🎬 Simulation Run Playback Video:</h4>
  <video width="480" height="480" controls autoplay loop muted playsinline style="max-width: 100%; height: auto; border: 1px solid #444; border-radius: 6px; background: #000;">
    <source src="data:video/mp4;base64,{b64_data}" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</div>'''
    except Exception as e:
        print(f"[Grader] Failed to process video HTML: {e}")
        return ""

def load_test_suite(assignment_name):
    suite_path = os.path.join(SOURCE_DIR, "assignments", assignment_name, "test_suite.py")
    if not os.path.exists(suite_path):
        # Local fallback if directory structured differently
        suite_path = os.path.join(os.path.dirname(__file__), "assignments", assignment_name, "test_suite.py")
        
    if not os.path.exists(suite_path):
        raise FileNotFoundError(f"Test suite not found at {suite_path}")
        
    spec = importlib.util.spec_from_file_location("test_suite", suite_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    print("=== UCT Micromouse Gradescope Autograder Runner ===")
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    global SUBMISSION_DIR, RESULTS_FILE
    import argparse
    parser = argparse.ArgumentParser(description="Gradescope Autograder Runner")
    parser.add_argument("--assignment", type=str, default=None, help="Assignment name override (e.g. milestone1_square, milestone2_maze, final_demo)")
    parser.add_argument("--submission", type=str, default=None, help="Submission directory")
    parser.add_argument("--results", type=str, default=None, help="Results output file path")
    args, _ = parser.parse_known_args()
    
    if args.submission:
        SUBMISSION_DIR = os.path.abspath(args.submission)
        print(f"[Grader] Overridden SUBMISSION_DIR: {SUBMISSION_DIR}")
    
    if args.results:
        RESULTS_FILE = os.path.abspath(args.results)
        print(f"[Grader] Overridden RESULTS_FILE: {RESULTS_FILE}")
    
    # 2. Find active assignment config
    if args.assignment:
        assignment_name = args.assignment.strip()
    else:
        active_assignment_file = os.path.join(SOURCE_DIR, "active_assignment.txt")
        if not os.path.exists(active_assignment_file):
            # Local fallback
            active_assignment_file = os.path.join(os.path.dirname(__file__), "active_assignment.txt")
            
        if os.path.exists(active_assignment_file):
            with open(active_assignment_file, "r") as f:
                assignment_name = f.read().strip()
        else:
            assignment_name = "milestone1" # default fallback
        
    print(f"[Grader] Active assignment: {assignment_name}")

    # Dynamically resolve default submission folder to workspace folders if not overridden
    if not args.submission:
        assignment_workspaces = {
            "milestone1_square": os.path.join(repo_root, "workspace", "task1_square"),
            "milestone2_maze": os.path.join(repo_root, "workspace", "task2_maze"),
            "final_demo": os.path.join(repo_root, "workspace", "final_task")
        }
        fallback_dir = assignment_workspaces.get(assignment_name)
        if fallback_dir and os.path.exists(fallback_dir):
            SUBMISSION_DIR = fallback_dir
            print(f"[Grader] Default SUBMISSION_DIR resolved to active workspace: {SUBMISSION_DIR}")
        else:
            print(f"[Grader] Default SUBMISSION_DIR resolved to: {SUBMISSION_DIR}")
    
    try:
        test_suite = load_test_suite(assignment_name)
    except Exception as e:
        write_results(0.0, f"System Error: Failed to load test suite for assignment '{assignment_name}': {e}")
        return

    # Early exit for Milestone 0 (log submission only, no simulator needed)
    if assignment_name == "milestone0_verification":
        print("[Grader] Milestone 0 log evaluation track detected.")
        try:
            log_path = os.path.join(SUBMISSION_DIR, "run_log.jsonl")
            if not os.path.exists(log_path):
                # Scan for any .jsonl file in the submission folder as fallback
                candidates = glob.glob(os.path.join(SUBMISSION_DIR, "*.jsonl"))
                if candidates:
                    log_path = candidates[0]
            score, feedback = test_suite.evaluate_log(log_path)
            write_results(score, feedback, "Milestone 0 Evaluation")
        except Exception as e:
            write_results(0.0, f"Grading Error: Failed to evaluate log submission: {e}", "Milestone 0 Evaluation")
        return

    # 3. Detect submission track (Simulink vs Python)
    print(f"[Grader] Scanning submission directory: {SUBMISSION_DIR}")
    
    # Clean up any student-submitted uct_mouse.py or micromouse.py files in Gradescope sandbox only
    if os.path.exists("/autograder"):
        for root, dirs, files in os.walk(SUBMISSION_DIR):
            for f in files:
                if f in ["uct_mouse.py", "micromouse.py"]:
                    target_path = os.path.join(root, f)
                    print(f"[Grader] Cleaning up student-submitted framework override: {target_path}")
                    try:
                        os.remove(target_path)
                    except Exception as e:
                        print(f"[Grader] Warning: Failed to remove {target_path}: {e}")

    # Check for Simulink track by looking for any folder ending in _ert_rtw
    ert_dirs = []
    for root, dirs, files in os.walk(SUBMISSION_DIR):
        for d in dirs:
            if d.endswith("_ert_rtw"):
                ert_dirs.append(os.path.join(root, d))
                
    track = None
    model_dir = None
    model_name = None
    main_file = None
    
    if ert_dirs:
        # Prefer UCT_KDeploy_ert_rtw if multiple
        target_dir = None
        for d in ert_dirs:
            if os.path.basename(d) == "UCT_KDeploy_ert_rtw":
                target_dir = d
                break
        if not target_dir:
            target_dir = ert_dirs[0]
            
        track = "simulink"
        model_dir = target_dir
        model_name = os.path.basename(target_dir)[:-8]  # Strip '_ert_rtw'
        print(f"[Grader] Track detected: Simulink")
        print(f"[Grader] Found code generation folder: {model_dir}")
        print(f"[Grader] Model name: {model_name}")
    else:
        # Check for Python track by looking for <assignment_name>.py or main.py
        main_candidates = []
        target_name = f"{assignment_name}.py"
        
        for root, dirs, files in os.walk(SUBMISSION_DIR):
            if target_name in files:
                main_candidates.append(os.path.join(root, target_name))
            if "main.py" in files:
                main_candidates.append(os.path.join(root, "main.py"))
                
        if main_candidates:
            target_main = None
            
            # 1. Prioritize files named exactly <assignment_name>.py
            for p in main_candidates:
                if os.path.basename(p) == target_name:
                    target_main = p
                    break
                    
            # 2. Prioritize files in a folder named after the active assignment (e.g., milestone1/)
            if not target_main:
                for p in main_candidates:
                    path_parts = p.split(os.sep)
                    if assignment_name in path_parts or any(assignment_name in part for part in path_parts):
                        target_main = p
                        break
                        
            # 3. Prioritize files under python/ directory
            if not target_main:
                for p in main_candidates:
                    if "/python/" in p or p.endswith("python/main.py"):
                        target_main = p
                        break
                        
            # 4. Fallback
            if not target_main:
                target_main = main_candidates[0]
                
            track = "python"
            main_file = target_main
            print(f"[Grader] Track detected: Python")
            print(f"[Grader] Found entry point: {main_file}")
        else:
            write_results(0.0, f"Submission Error: Neither a Simulink code generation folder (*_ert_rtw), a Python entry point ({target_name}), nor a standard 'main.py' was found in your submission.")
            return

    # 4. Compilation if Simulink track
    client_bin = os.path.join(tempfile.gettempdir(), "simulink_client")
    if track == "simulink":
        print("[Grader] Compiling Simulink deployment code...")
        
        # Locate wrapper files in SOURCE_DIR
        pc_main = os.path.join(SOURCE_DIR, "PC_client_main.c")
        sim_wrapper = os.path.join(SOURCE_DIR, "simulink_wrapper.c")
        sim_header = os.path.join(SOURCE_DIR, "simulink_wrapper.h")
        
        # Verify wrapper files exist (if not in SOURCE_DIR, fallback to repo paths)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if not os.path.exists(pc_main):
            pc_main = os.path.join(repo_root, "matlab", "simulink", "PC_client_main.c")
        if not os.path.exists(sim_wrapper):
            sim_wrapper = os.path.join(repo_root, "firmware", "src", "kernel", "src", "simulink_wrapper.c")
        if not os.path.exists(sim_header):
            sim_header = os.path.join(repo_root, "firmware", "src", "kernel", "inc", "simulink_wrapper.h")
            
        if not os.path.exists(pc_main) or not os.path.exists(sim_wrapper):
            write_results(0.0, "System Error: Missing standalone main client or simulink wrappers in autograder package.")
            return
            
        # Find all generated sources in model directory (exclude ert_main.c)
        model_sources = glob.glob(os.path.join(model_dir, "*.c"))
        model_sources = [f for f in model_sources if os.path.basename(f) != "ert_main.c"]
        
        all_sources = [pc_main, sim_wrapper] + model_sources
        
        # Choose compiler
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            write_results(0.0, "System Error: No suitable C compiler (gcc or clang) found in the autograder environment.")
            return
            
        # Build compile command
        cmd = [
            compiler,
            "-O2",
            f"-DMODEL_NAME={model_name}",
            f"-I{model_dir}",
            f"-I{os.path.dirname(sim_header)}", # wrapper header folder
            f"-I{SOURCE_DIR}" # also include source dir
        ]
        cmd.extend(all_sources)
        cmd.extend(["-o", client_bin, "-lm"])
        
        print(f"[Grader] Compiler command: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30.0)
            if res.returncode != 0:
                feedback = (
                    f"Compilation Error: Your Simulink generated C code failed to compile.\n\n"
                    f"--- Compiler Output (stdout) ---\n{res.stdout}\n\n"
                    f"--- Compiler Error (stderr) ---\n{res.stderr}"
                )
                write_results(0.0, feedback, "Compilation Check")
                return
            print("[Grader] Compilation succeeded.")
        except subprocess.TimeoutExpired:
            write_results(0.0, "Compilation Error: C compilation process timed out after 30 seconds.", "Compilation Check")
            return
        except Exception as e:
            write_results(0.0, f"Compilation Error: Failed to invoke compiler: {e}", "Compilation Check")
            return

    # 5. Execute Multi-Run Simulation Tests
    test_runs = getattr(test_suite, "TEST_RUNS", [("Standard Run", 1.0, 0.08, 0.08, False)])
    
    sim_script = os.path.join(SOURCE_DIR, "physics_sim.py")
    if not os.path.exists(sim_script):
        sim_script = os.path.join(repo_root, "tools", "physics_sim.py")
    if not os.path.exists(sim_script):
        sim_script = os.path.join(os.path.dirname(__file__), "..", "physics_sim.py")
    if not os.path.exists(sim_script):
        write_results(0.0, f"System Error: Simulator backend script 'physics_sim.py' not found (looked in {SOURCE_DIR}, {repo_root}/tools).")
        return
        
    # Check for student-submitted dynamic simulation config (sim_config.json)
    student_config = None
    for candidate in ["sim_config.json", "simulation_config.json"]:
        p = os.path.join(SUBMISSION_DIR, candidate)
        if os.path.exists(p):
            student_config = p
            print(f"[Grader] Discovered Student Identified Simulation Config: {student_config}")
            break

    total_score = 0.0
    gradescope_tests = []
    session_start_time = time.time()
    MAX_SESSION_SECONDS = 240.0  # 4.0 minutes hard budget for whole autograder suite
    
    for idx, (run_name, weight, imb_val, slip_val, is_hidden) in enumerate(test_runs):
        elapsed_total = time.time() - session_start_time
        if elapsed_total > MAX_SESSION_SECONDS:
            print(f"[Grader] Overall autograder time budget exceeded ({elapsed_total:.1f}s > {MAX_SESSION_SECONDS}s). Skipping {run_name}.")
            max_test_points = round(weight * 60.0, 2)
            run_visibility = "after_due_date" if is_hidden else "visible"
            gradescope_tests.append({
                "name": run_name,
                "score": 0.0,
                "max_score": max_test_points,
                "status": "failed",
                "output": f"<p>Evaluation timed out: overall autograder execution time budget reached ({elapsed_total:.1f}s).</p>",
                "output_format": "html",
                "visibility": run_visibility
            })
            continue

        print(f"\n[Grader] === Executing {run_name} (Weight: {weight*100:.0f}%, Imbalance: {imb_val}, Slip: {slip_val}) ===")
        
        def run_single_simulation(seed_val, is_video):
            sim_cmd = [
                sys.executable,
                "-u",
                sim_script,
                "--headless",
                "--map", getattr(test_suite, "MAP", "empty"),
                "--imbalance", str(imb_val),
                "--slip", str(slip_val),
                "--json-log", TRAJECTORY_JSON,
                "--video", VIDEO_PATH if is_video else "",
                "--max-time", str(getattr(test_suite, "TIME_LIMIT", 45.0)),
                "--seed", str(seed_val)
            ]
            if student_config:
                sim_cmd.extend(["--config", student_config])
            
            if os.path.exists(TRAJECTORY_JSON):
                try: os.remove(TRAJECTORY_JSON)
                except Exception: pass
                    
            sim_log_path = os.path.join(tempfile.gettempdir(), "simulator_backend.log")
            if os.path.exists(sim_log_path):
                try: os.remove(sim_log_path)
                except Exception: pass
                    
            try:
                sim_log_file = open(sim_log_path, "w")
                sim_proc = subprocess.Popen(
                    sim_cmd,
                    stdout=sim_log_file,
                    stderr=sim_log_file,
                    text=True
                )
                sim_log_file.close()
            except Exception as e:
                return {
                    "score": 0.0,
                    "feedback": f"System Error: Failed to start simulation backend: {e}",
                    "stdout": "", "stderr": "", "simout": "", "crashed": True,
                    "traj_exists": False
                }
                
            simulator_ready = False
            exited_early = False
            start_wait = time.time()
            while time.time() - start_wait < 20.0:
                poll_status = sim_proc.poll()
                if poll_status is not None:
                    exited_early = True
                    break
                if os.path.exists(sim_log_path):
                    try:
                        with open(sim_log_path, "r") as f:
                            if "Waiting for student script to connect" in f.read():
                                simulator_ready = True
                                break
                    except Exception:
                        pass
                time.sleep(0.05)
                
            if not simulator_ready:
                sim_proc.terminate()
                try: sim_proc.wait(timeout=2.0)
                except Exception: sim_proc.kill()
                log_tail = ""
                if os.path.exists(sim_log_path):
                    try:
                        with open(sim_log_path, "r") as f:
                            log_tail = "".join(f.readlines()[-15:])
                    except Exception: pass
                return {
                    "score": 0.0,
                    "feedback": f"System Error: Simulator failed to start or bind to port 8000.\n\n{log_tail}",
                    "stdout": "", "stderr": "", "simout": log_tail, "crashed": True,
                    "traj_exists": False
                }
                
            client_env = os.environ.copy()
            client_env["GRADESCOPE_AUTOGRADER"] = "1"
            
            if track == "python":
                client_cmd = [sys.executable, main_file]
                python_paths = [SOURCE_DIR, os.path.dirname(main_file), os.path.join(repo_root, "python")]
                if "PYTHONPATH" in os.environ:
                    python_paths.append(os.environ["PYTHONPATH"])
                client_env["PYTHONPATH"] = os.path.pathsep.join(python_paths)
                client_cwd = os.path.dirname(main_file)
            else:
                client_cmd = [client_bin]
                client_cwd = tempfile.gettempdir()
                
            try:
                client_proc = subprocess.Popen(
                    client_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=client_env,
                    cwd=client_cwd,
                    text=True
                )
            except Exception as e:
                try:
                    if sys.platform == "win32":
                        sim_proc.terminate()
                    else:
                        sim_proc.send_signal(signal.SIGINT)
                    sim_proc.wait(timeout=2.0)
                except Exception:
                    sim_proc.kill()
                return {
                    "score": 0.0,
                    "feedback": f"Execution Error: Failed to start student script/binary: {e}",
                    "stdout": "", "stderr": "", "simout": "", "crashed": True,
                    "traj_exists": False
                }
                
            time_limit = getattr(test_suite, "TIME_LIMIT", 45.0)
            # In fast-sim autograder mode, a 45s simulated run takes ~1s.
            # Allow up to 25s wall-clock time per run to quickly catch hung loops.
            max_duration = min(time_limit + 5.0, 25.0) if os.path.exists("/autograder") else (time_limit + 5.0)
            start_time = time.time()
            client_exited = False
            
            while time.time() - start_time < max_duration:
                if not client_exited and client_proc.poll() is not None:
                    client_exited = True
                    time.sleep(0.5)
                if sim_proc.poll() is not None:
                    break
                time.sleep(0.2)
                
            if client_proc.poll() is None:
                client_proc.terminate()
                try: client_proc.wait(timeout=2.0)
                except Exception: client_proc.kill()
                
            if sim_proc.poll() is None:
                try:
                    if sys.platform == "win32":
                        # Windows does not support sending arbitrary SIGINT to child subprocesses
                        sim_proc.terminate()
                    else:
                        sim_proc.send_signal(signal.SIGINT)
                    sim_proc.wait(timeout=3.0)
                except Exception:
                    sim_proc.kill()
                
            client_stdout, client_stderr = client_proc.communicate()
            
            sim_stdout = ""
            if os.path.exists(sim_log_path):
                try:
                    with open(sim_log_path, "r") as f:
                        sim_stdout = f.read()
                except Exception: pass
                
            run_score = 0.0
            run_feedback = ""
            is_crashed = False
            traj_exists = os.path.exists(TRAJECTORY_JSON) and os.path.getsize(TRAJECTORY_JSON) > 0
            
            if not traj_exists:
                run_feedback = (
                    f"Execution Error: No simulation trajectory was recorded.\n"
                    f"Your script or binary did not connect to the simulator on port 8000.\n\n"
                    f"--- Console Output (stdout) ---\n{client_stdout}\n\n"
                    f"--- Error Output (stderr) ---\n{client_stderr}\n"
                )
                is_crashed = True
            else:
                try:
                    with open(TRAJECTORY_JSON, "r") as f:
                        tdata = json.load(f)
                        is_crashed = tdata.get("crashed", False)
                    try:
                        raw_score, run_feedback = test_suite.evaluate_run(TRAJECTORY_JSON, is_hidden=is_hidden)
                    except TypeError:
                        raw_score, run_feedback = test_suite.evaluate_run(TRAJECTORY_JSON)
                    run_score = raw_score
                except Exception as e:
                    run_feedback = f"System Error: Failed to evaluate simulation results: {e}"
                    is_crashed = True
                    
            return {
                "score": run_score,
                "feedback": run_feedback,
                "stdout": client_stdout,
                "stderr": client_stderr,
                "simout": sim_stdout,
                "crashed": is_crashed,
                "traj_exists": traj_exists,
                "seed": seed_val
            }

        # Execute simulation trial
        base_seed = getattr(test_suite, "SEED", 42) + idx
        trial = run_single_simulation(base_seed, is_video=(idx == 0))
        
        run_score = trial["score"]
        run_feedback = trial["feedback"]
        client_stdout = trial["stdout"]
        client_stderr = trial["stderr"]
        sim_stdout = trial["simout"]
        
        max_test_points = round(weight * 60.0, 2)
        test_points = round((run_score / 100.0) * max_test_points, 2)
        total_score += test_points
        
        run_visibility = "after_due_date" if is_hidden else "visible"
        
        # Generate HTML visualizations
        svg_html = generate_trajectory_svg(TRAJECTORY_JSON)
        video_html = get_video_html(VIDEO_PATH) if (idx == 0 and os.path.exists(VIDEO_PATH)) else ""
        
        import html
        escaped_feedback = html.escape(run_feedback)
        escaped_stdout = html.escape(client_stdout) if client_stdout else ""
        escaped_stderr = html.escape(client_stderr) if client_stderr else ""
        escaped_simout = html.escape(sim_stdout) if sim_stdout else ""
        
        html_sections = []
        html_sections.append(f"<h3 style='margin-top:0;'>=== {run_name} ===</h3>")
        html_sections.append(f"<p><strong>Weight:</strong> {weight*100:.0f}% &nbsp;|&nbsp; <strong>Run Score:</strong> {run_score:.1f}% &nbsp;|&nbsp; <strong>Points:</strong> {test_points:.2f} / {max_test_points:.2f} pts &nbsp;|&nbsp; <strong>Visibility:</strong> {run_visibility.replace('_', ' ').capitalize()}</p>")
        
        if svg_html:
            html_sections.append(svg_html)
        if video_html:
            html_sections.append(video_html)
            
        html_sections.append(f"<pre style='background:#1e1e1e; color:#d4d4d4; padding:12px; border-radius:6px; font-family:monospace; font-size:12px; line-height:1.4; overflow-x:auto;'>{escaped_feedback}</pre>")
        
        if escaped_stdout:
            html_sections.append(f"<details style='margin-top:10px;'><summary style='cursor:pointer; font-weight:bold;'>Student Console Output (stdout)</summary><pre style='background:#1e1e1e; color:#d4d4d4; padding:12px; border-radius:6px; font-family:monospace; font-size:12px; margin-top:6px;'>{escaped_stdout}</pre></details>")
        if escaped_stderr:
            html_sections.append(f"<details style='margin-top:10px;'><summary style='cursor:pointer; font-weight:bold; color:#ff6b6b;'>Student Error Output (stderr)</summary><pre style='background:#2a1818; color:#ff8080; padding:12px; border-radius:6px; font-family:monospace; font-size:12px; margin-top:6px;'>{escaped_stderr}</pre></details>")
        if escaped_simout:
            html_sections.append(f"<details style='margin-top:10px;'><summary style='cursor:pointer; font-weight:bold;'>Simulator Backend Output</summary><pre style='background:#1e1e1e; color:#888; padding:12px; border-radius:6px; font-family:monospace; font-size:12px; margin-top:6px;'>{escaped_simout}</pre></details>")
            
        joined_run_html = "".join(html_sections)
        
        test_status = "passed" if run_score > 0.0 else "failed"
        
        gradescope_tests.append({
            "name": run_name,
            "score": test_points,
            "max_score": max_test_points,
            "status": test_status,
            "output": joined_run_html,
            "output_format": "html",
            "visibility": run_visibility
        })
        
        print(f"[Grader] Completed {run_name}: Score {run_score}/100 -> {test_points}/{max_test_points} pts")

    # 6. Write Consolidated Results JSON File
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    final_score = round(total_score, 2)
    final_percent = round((final_score / 60.0) * 100.0, 1)
    
    results = {
        "score": final_score,
        "max_score": 60.0,
        "output": f"<h3 style='margin-top:0;'>Milestone 1 Autograder Trajectory Score: {final_score:.2f} / 60.00 pts ({final_percent}%)</h3>",
        "output_format": "html",
        "visibility": "visible",
        "tests": gradescope_tests
    }
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[Grader] All test runs finished. Final autograder score: {final_score}/60.00 pts ({final_percent}%) written to {RESULTS_FILE}")

if __name__ == "__main__":
    main()
