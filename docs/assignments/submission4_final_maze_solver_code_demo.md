# EEE3097/8/9S Micromouse 2026: Submission 4
## Final Maze Solver Code & Demo (25% of Course Mark)

---

### 1. Objective
Design and implement the complete autonomous intelligence for your Micromouse. The robot must explore a 4x6 grid maze to discover its wall layout, build a topological map of the grid, calculate the optimal shortest path back to the starting cell (or to the target cell), and execute a high-speed "solving run" without colliding with any walls.

#### **Specific Learning Objectives:**
* Interfacing with three VL53L0X Time-of-Flight (ToF) sensors and calibrating wall detection thresholds.
* Fusing high-resolution wheel encoders with the gyroscope yaw rate to track coordinate state $(x, y)$ and heading orientation (North, East, South, West).
* Implementing grid-based exploration state machines (e.g. Floodfill or Depth-First Search).
* Implementing shortest-path planning solvers (e.g., A*, Dijkstra, or BFS) to calculate optimal routing.
* Tuning velocity profiles (accelerations, corner deceleration limits) to transition smoothly between straight segments and cornering.

---

### 2. Step-by-Step Implementation Guide

#### **Step 1: Exploration & Mapping Run**
* Place your mouse at the starting cell $(0,0)$.
* The mouse must autonomously explore the 4x6 maze. As it enters each cell, it must read its ToF sensors, classify wall presence, and update its internal map array.
* Implement active wall-centering using side ToF measurements to dynamically correct steering drift.

#### **Step 2: Path Solving**
* Once exploration is completed, your algorithm must import the mapped grid matrix.
* Calculate the shortest path from the starting cell $(0,0)$ to the target cell.
* Return the mouse autonomously to $(0,0)$, re-align heading orientation, and halt to prepare for the speed sprint.

#### **Step 3: High-Speed Speed Run**
* Load the calculated shortest path array.
* Execute a high-speed sprint directly to the target cell.
* Your velocity planner must merge consecutive straight cells into a single acceleration-cruise-deceleration profile (rather than stopping at every cell boundary).
* The run is successfully complete when the mouse stops autonomously and safely within the target cell.

---

### 3. Deliverables (Gradescope Submission)
To package your final submission, run the following command from your repository root:
```bash
python tools/package_submission.py --task final_demo --src workspace/final_task/
```
This script will perform dynamic syntax and formatting checks and generate a single **`submission_final_demo.zip`** in your project root. Upload this ZIP AND your **`run_video.mp4`** separately to Gradescope (Gradescope allows you to drag-and-drop both files into the submission portal together).

The submission consists of:
1. **Your ZIP Package (`submission_final_demo.zip`):**
   * **Your Solving Code:** Automatically compiled and zipped from your workspace directory (includes `main.py` and any subfolders/libraries recursively).
   * **Physical Telemetry Log (`run_log.jsonl`):** Automatically detected by the packager tool from your project directory (no need to copy it manually).
2. **Your Physical Run Video (`run_video.mp4`):**
   * Uploaded as a **separate file** alongside your ZIP. The video must start with a **3-second close-up of your Student Card** followed by the uncut mapping and high-speed solving runs.

#### **Testing the Autograder Offline (Locally)**
You are highly encouraged to test your algorithm against the grading suite locally on your laptop before uploading to Gradescope. To run the full multi-test evaluation suite locally, run this command from the repository root:
```bash
python tools/autograder/grade_runner.py
```
This script runs the local simulator backend, automatically detects and executes your code from **`workspace/final_task/`**, runs it through the test scenarios, and outputs the resulting score sheet directly to your terminal.

*Note: If you want to run the autograder on a different folder (e.g. a solutions or test directory), you can override the source folder using the `--submission` flag:*
```bash
python tools/autograder/grade_runner.py --submission path/to/your/folder
```

---

### 4. Video Requirements & Academic Honesty Declaration
To verify that your physical run is authentic, the video must strictly adhere to the following sequence:
1. **Student Card Close-up:** The video **MUST start with a clear, readable close-up of your physical Student Card** for at least 3 seconds (declaring this is your own work).
2. **Setup:** Show the mouse positioned at the starting cell.
3. **Traversals:** Capture the mapping run, the return-to-start orientation reset, and the final high-speed run to the target cell without cuts.

---

### 5. Code & Log Correlation Verification (Anti-Cheat Check)
* **Hardware ID Check:** The `"uid"` field represents your microcontroller's unique device ID. While this is not registered in advance, the course convenors check the submitted logs for duplicate UIDs. Submitting logs with identical UIDs under different student accounts indicates shared files/hardware runs and will trigger a plagiarism audit.
* **Code Match Check:** The autograder compiles and computes an FNV-1a checksum hash of your submitted code and matches it against the `"hash"` field in your telemetry header. **Mismatched hashes will result in an immediate submission rejection.**

---

### 6. Evaluation Criteria & Grading Rubric
Your Gradescope submission is evaluated across three parts:

* **Part A: Co-Simulation Speed & Accuracy (60% of Milestone Mark):**
  Your solver is tested in procedurally generated mazes under perturbations. The simulation runs up to a **90-second limit** and automatically completes when the mouse is detected to be **stationary for 3.0 seconds** after initial movement.
  
  The autograder score is calculated out of 100 points as follows:
  * **Exploration Progress Score (80 points max):** Graded proportionally based on the closest distance the mouse achieves to the maze center zone $(1.0, 1.0)$ during the run. Reaching the center zone awards the full **80 pts**.
  * **Speed Run Traversal Bonus (20 points max):** Unlocked only if the center is successfully reached. Evaluated continuously based on the simulation elapsed time:
    * $\text{Time} \le 30.0$ seconds: Full **20 pts**
    * $30.0\text{ s} < \text{Time} \le 90.0\text{ s}$: Scales linearly from **20 down to 5 pts**
    * $\text{Time} > 90.0$ seconds: **0 pts**
  * **Applied Penalties:**
    * **Timeout Penalty ($-10$ points):** Subtracted if the controller fails to stop within the 90-second limit.
    * *Collision Note:* Contacting a wall halts the simulation immediately, naturally capping your score based only on the progress achieved prior to the crash. No additional numerical collision penalties are subtracted.

* **Part B: Physical Run Verification (30% of Milestone Mark):**
  Tutors will evaluate your submitted physical demonstration video (`run_video.mp4`) and verify hardware exploration and solving speed-run performance. Marks are awarded for active wall-centering, mapping reliability, correct shortest-path planning, and successful high-speed sprint to the target cell without manual assists or crashes.

* **Part C: Submission Compliance (10% of Milestone Mark):**
  Evaluated by tutors on instruction compliance:
  * **All Files Included (5%):** Correct zipping of source code workspace and valid FNV-1a checksum matched physical telemetry log file (`run_log.jsonl`).
  * **Student Card Close-up (5%):** The physical demo video begins with a clear, readable 3-second close-up of your Student Card.

---

> [!NOTE]
> **Grading Adaptation Policy:** The grading thresholds, coefficients, and parameters detailed above serve as baseline targets. Course staff reserve the right to adjust or tailor specific parameters post-submission to ensure final grades are highly representative of actual design and hardware performance.
