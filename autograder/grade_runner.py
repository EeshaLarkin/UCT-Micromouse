#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import json
import signal
import glob
import importlib.util
import shutil

# 1. Path Resolution
if os.path.exists("/autograder"):
    SUBMISSION_DIR = "/autograder/submission"
    RESULTS_FILE = "/autograder/results/results.json"
    SOURCE_DIR = "/autograder/source"
    VIDEO_PATH = "/autograder/results/run.mp4"
    TRAJECTORY_JSON = "/tmp/trajectory.json"
else:
    # Local mock mode
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SUBMISSION_DIR = os.path.join(base_dir, "python")  # mock submission is the local python dir
    RESULTS_FILE = os.path.join(base_dir, "autograder", "results.json")
    SOURCE_DIR = os.path.join(base_dir, "autograder")
    VIDEO_PATH = os.path.join(base_dir, "autograder", "run.mp4")
    TRAJECTORY_JSON = os.path.join(base_dir, "autograder", "trajectory.json")

def write_results(score, feedback, test_name="Autograder Evaluation"):
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    results = {
        "score": score,
        "max_score": 100.0,
        "output": feedback,
        "visibility": "visible",
        "tests": [
            {
                "name": test_name,
                "score": score,
                "max_score": 100.0,
                "output": feedback,
                "visibility": "visible"
            }
        ]
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[Grader] Results written to {RESULTS_FILE} with score {score}")

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
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    global SUBMISSION_DIR, RESULTS_FILE
    import argparse
    parser = argparse.ArgumentParser(description="Gradescope Autograder Runner")
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
    
    try:
        test_suite = load_test_suite(assignment_name)
    except Exception as e:
        write_results(0.0, f"System Error: Failed to load test suite for assignment '{assignment_name}': {e}")
        return

    # 3. Detect submission track (Simulink vs Python)
    print(f"[Grader] Scanning submission directory: {SUBMISSION_DIR}")
    
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
    client_bin = "/tmp/simulink_client"
    if track == "simulink":
        print("[Grader] Compiling Simulink deployment code...")
        
        # Locate wrapper files in SOURCE_DIR
        pc_main = os.path.join(SOURCE_DIR, "PC_client_main.c")
        sim_wrapper = os.path.join(SOURCE_DIR, "simulink_wrapper.c")
        sim_header = os.path.join(SOURCE_DIR, "simulink_wrapper.h")
        
        # Verify wrapper files exist (if not in SOURCE_DIR, fallback to repo paths)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if not os.path.exists(pc_main):
            pc_main = os.path.join(repo_root, "matlab", "simulink", "PC_client_main.c")
        if not os.path.exists(sim_wrapper):
            sim_wrapper = os.path.join(repo_root, "src", "kernel", "src", "simulink_wrapper.c")
        if not os.path.exists(sim_header):
            sim_header = os.path.join(repo_root, "src", "kernel", "inc", "simulink_wrapper.h")
            
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

    # 5. Run Simulator
    # Ensure any old simulator or client processes are cleared
    # (Not strictly necessary in sandboxed Docker, but good practice)
    
    sim_script = os.path.join(SOURCE_DIR, "physics_sim.py")
    # Local fallback
    if not os.path.exists(sim_script):
        sim_script = os.path.join(repo_root, "tools", "physics_sim.py")
        
    sim_cmd = [
        sys.executable,
        "-u",
        sim_script,
        "--headless",
        "--map", getattr(test_suite, "MAP", "empty"),
        "--imbalance", str(getattr(test_suite, "IMBALANCE", 0.08)),
        "--slip", str(getattr(test_suite, "SLIP", 0.08)),
        "--json-log", TRAJECTORY_JSON,
        "--video", VIDEO_PATH,
        "--max-time", str(getattr(test_suite, "TIME_LIMIT", 45.0))
    ]
    if hasattr(test_suite, "SEED") and test_suite.SEED is not None:
        sim_cmd += ["--seed", str(test_suite.SEED)]
        
    print(f"[Grader] Spawning simulator process: {' '.join(sim_cmd)}")
    
    # Clean up old trajectory file and log file
    if os.path.exists(TRAJECTORY_JSON):
        try:
            os.remove(TRAJECTORY_JSON)
        except Exception:
            pass
            
    sim_log_path = "/tmp/simulator_backend.log"
    if os.path.exists(sim_log_path):
        try:
            os.remove(sim_log_path)
        except Exception:
            pass

    try:
        # Redirect stdout and stderr to a file to prevent pipe buffer blocks
        sim_log_file = open(sim_log_path, "w")
        sim_proc = subprocess.Popen(
            sim_cmd,
            stdout=sim_log_file,
            stderr=sim_log_file,
            text=True
        )
        sim_log_file.close()
    except Exception as e:
        write_results(0.0, f"System Error: Failed to start simulation backend: {e}")
        return
        
    # Wait for simulator to bind socket and show readiness in the logs
    print("[Grader] Waiting for simulator to start listening on port 8000...")
    simulator_ready = False
    start_wait = time.time()
    while time.time() - start_wait < 8.0:
        # Check if process has exited
        if sim_proc.poll() is not None:
            break
            
        # Check log file contents
        if os.path.exists(sim_log_path):
            try:
                with open(sim_log_path, "r") as f:
                    log_content = f.read()
                    if "Waiting for student script to connect" in log_content:
                        simulator_ready = True
                        break
            except Exception:
                pass
        time.sleep(0.1)
        
    if not simulator_ready:
        sim_proc.terminate()
        try:
            sim_proc.wait(timeout=2.0)
        except Exception:
            sim_proc.kill()
        
        log_content = ""
        if os.path.exists(sim_log_path):
            try:
                with open(sim_log_path, "r") as f:
                    log_content = f.read()
            except Exception:
                pass
        write_results(0.0, f"System Error: Simulator failed to start or bind to port 8000 within timeout.\nLog Content:\n{log_content}")
        return

    print("[Grader] Simulator is ready and listening.")

    # 6. Run Student Client
    client_env = os.environ.copy()
    client_env["GRADESCOPE_AUTOGRADER"] = "1"
    
    if track == "python":
        client_cmd = [sys.executable, main_file]
        # Override PYTHONPATH to prioritize our bundled mock uct_mouse library
        # (Fallbacks to SOURCE_DIR first)
        python_paths = [SOURCE_DIR, os.path.dirname(main_file)]
        if "PYTHONPATH" in os.environ:
            python_paths.append(os.environ["PYTHONPATH"])
        client_env["PYTHONPATH"] = os.path.pathsep.join(python_paths)
        client_cwd = os.path.dirname(main_file)
    else:
        client_cmd = [client_bin]
        client_cwd = "/tmp"
        
    print(f"[Grader] Launching student client: {' '.join(client_cmd)}")
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
        # Shutdown simulator
        sim_proc.send_signal(signal.SIGINT)
        try:
            sim_proc.wait(timeout=2.0)
        except Exception:
            sim_proc.kill()
        write_results(0.0, f"Execution Error: Failed to start student script/binary: {e}")
        return

    # 7. Monitor both processes
    time_limit = getattr(test_suite, "TIME_LIMIT", 45.0)
    max_duration = time_limit + 10.0 # wall-clock safety buffer
    start_time = time.time()
    
    client_exited = False
    timed_out = False
    
    while time.time() - start_time < max_duration:
        # Check client
        if not client_exited and client_proc.poll() is not None:
            client_exited = True
            print("[Grader] Student client exited. Waiting for simulator to clean up...")
            time.sleep(1.5)
            
        # Check simulator
        if sim_proc.poll() is not None:
            print("[Grader] Simulator backend exited.")
            break
            
        time.sleep(0.5)
    else:
        print("[Grader] Safety wall-clock timeout exceeded.")
        timed_out = True

    # 8. Cleanup and retrieve logs
    # Terminate student client
    if client_proc.poll() is None:
        print("[Grader] Terminating student client process...")
        client_proc.terminate()
        try:
            client_proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            client_proc.kill()
            
    # Send SIGINT to simulator so it runs its `finally:` block and dumps the JSON telemetry log
    if sim_proc.poll() is None:
        print("[Grader] Sending SIGINT to simulator for graceful telemetry dump...")
        sim_proc.send_signal(signal.SIGINT)
        try:
            sim_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            print("[Grader] Simulator did not exit. Force killing...")
            sim_proc.kill()
            
    # Gather logs
    client_stdout, client_stderr = client_proc.communicate()
    
    sim_stdout = ""
    sim_stderr = ""
    if os.path.exists(sim_log_path):
        try:
            with open(sim_log_path, "r") as f:
                sim_stdout = f.read()
        except Exception as e:
            sim_stdout = f"Error reading simulator log file: {e}"
    
    # 9. Evaluate
    if not os.path.exists(TRAJECTORY_JSON) or os.path.getsize(TRAJECTORY_JSON) == 0:
        feedback = (
            f"Execution Error: No simulation trajectory was recorded.\n"
            f"Your script or binary did not connect to the simulator on port 8000.\n\n"
            f"--- Student Console Output (stdout) ---\n{client_stdout}\n\n"
            f"--- Student Error Output (stderr) ---\n{client_stderr}\n\n"
            f"--- Simulator Output ---\n{sim_stdout}\n{sim_stderr}"
        )
        write_results(0.0, feedback, f"{assignment_name.upper()} Grading")
        return
        
    try:
        score, run_feedback = test_suite.evaluate_run(TRAJECTORY_JSON)
    except Exception as e:
        feedback = (
            f"System Error: Failed to evaluate simulation results: {e}\n\n"
            f"--- Student Console Output (stdout) ---\n{client_stdout}\n\n"
            f"--- Student Error Output (stderr) ---\n{client_stderr}"
        )
        write_results(0.0, feedback, f"{assignment_name.upper()} Grading")
        return

    # 10. Compile final feedback reports
    full_report = [run_feedback, ""]
    if timed_out:
        full_report.append("[Warning] The student program was terminated because it exceeded the max wall-clock duration limit.")
        
    if client_stdout:
        full_report.append(f"--- Student Output (stdout) ---\n{client_stdout}")
    if client_stderr:
        full_report.append(f"--- Student Errors (stderr) ---\n{client_stderr}")
    if sim_stdout or sim_stderr:
        full_report.append(f"--- Simulator Logs ---\n{sim_stdout}\n{sim_stderr}")

    final_feedback = "\n".join(full_report)
    write_results(score, final_feedback, f"{assignment_name.upper()} Evaluation")

if __name__ == "__main__":
    main()
