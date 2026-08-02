# EEE3097/8/9S Micromouse 2026: Submission 4
## Final Maze Solver Code & Demo (25% of Course Mark)

---

### 1. Objective
Design and implement the complete autonomous intelligence for your Micromouse. The robot must explore a 4x6 grid maze to discover its wall layout, build a map, calculate the optimal shortest path back to the starting cell (or to the target cell), and execute a high-speed "solving run" without colliding with any walls.

#### **Specific Learning Objectives:**
* Calibrate distance thresholds for three VL53L0X ToF sensors.
* Fuse high-resolution wheel encoders with the gyroscope yaw rate to track coordinate state $(x, y)$ and heading direction.
* Implement grid-based exploration state machines (e.g. Floodfill or DFS).
* Implement shortest-path planning solvers (e.g., Dijkstra, A*, or BFS) to calculate optimal routing.
* Design velocity profiles to transition between straightaways and turns.

---

### 2. Step-by-Step Implementation Guide
* **Exploration & Mapping:** Drive the mouse autonomously from $(0,0)$ to explore the grid. Keep the mouse centered using side ToF sensors.
* **Path Solving:** Once the maze is mapped, calculate the shortest path to the target. Return to $(0,0)$ and stop.
* **High-Speed Speed Run:** Load the calculated shortest path and sprint directly to the target. Merge consecutive straight cells into a single acceleration-cruise-deceleration profile. Stop autonomously inside the target.

---

### 3. Deliverables (Gradescope Submission)
Run the packaging command from your repository root:
```bash
python tools/package_submission.py --task final_demo --src workspace/final_task/
```
Upload the resulting **`submission_final_demo.zip`** AND your **`run_video.mp4`** separately to Gradescope (Gradescope allows you to drag-and-drop both files into the submission portal together).

The submission consists of:
1.  **Your ZIP Package (`submission_final_demo.zip`):**
    *   **Your Solving Code:** Automatically compiled and zipped from your workspace directory (includes `main.py` and any subfolders/libraries recursively).
    *   **Physical Telemetry Log (`run_log.jsonl`):** Automatically detected by the packager tool from your project directory (no need to copy it manually).
2.  **Your Physical Run Video (`run_video.mp4`):**
    *   Uploaded as a **separate file** alongside your ZIP. The video must start with a **3-second close-up of your Student Card** followed by the uncut mapping and high-speed solving runs.

---

### 4. Code & Log Check (Anti-Cheat)
* **Code Match Check:** The autograder compiles/hashes your code and verifies it matches the FNV-1a `"hash"` checksum in your telemetry header.
* **Hardware ID Check:** Microcontroller Device UIDs are tracked. Shared logs under different student accounts will trigger a plagiarism audit.

---

### 5. Evaluation Criteria & Grading Rubric
Your Gradescope submission is evaluated across two parts:

*   **Part A: Co-Simulation Speed & Accuracy (60% of Milestone Mark):**
    Your solver is tested in procedurally generated mazes under perturbations. The simulation runs up to a **90-second limit** and automatically completes when the mouse is detected to be **stationary for 3.0 seconds** after initial movement.
    
    The autograder score is calculated out of 100 points as follows:
    *   **Exploration Progress Score (80 points max):** Graded proportionally based on the closest distance the mouse achieves to the maze center zone $(1.0, 1.0)$ during the run. Reaching within a $0.25\text{ m}$ radius of the center target awards the full **80 pts**.
    *   **Speed Run Traversal Bonus (20 points max):** Unlocked only if the center is successfully reached. Evaluated continuously based on the simulation elapsed time:
        *   $\text{Time} \le 30.0$ seconds: Full **20 pts**
        *   $30.0\text{ s} < \text{Time} \le 90.0\text{ s}$: Scales linearly from **20 down to 5 pts**
        *   $\text{Time} > 90.0$ seconds: **0 pts**
    *   **Applied Penalties:**
        *   **Timeout Penalty ($-10$ points):** Subtracted if the controller fails to stop within the 90-second limit.
        *   *Collision Note:* Contacting a wall halts the simulation immediately, naturally capping your score based only on the progress achieved prior to the crash. No additional numerical collision penalties are subtracted.

*   **Part B: Physical Run Verification (30% of Milestone Mark):**
    Tutors will evaluate your submitted physical demonstration video (`run_video.mp4`) and verify hardware exploration and solving speed-run performance. Marks are awarded for active wall-centering, mapping reliability, correct shortest-path planning, and successful high-speed sprint to the target cell without manual assists or crashes.

*   **Part C: Submission Compliance (10% of Milestone Mark):**
    Evaluated by tutors on instruction compliance:
    *   **All Files Included (5%):** Correct zipping of source code workspace and valid FNV-1a checksum matched physical telemetry log file (`run_log.jsonl`).
    *   **Student Card Close-up (5%):** The physical demo video begins with a clear, readable 3-second close-up of your Student Card.

---

> [!NOTE]
> **Grading Adaptation Policy:** The grading thresholds, coefficients, and parameters detailed above serve as baseline targets. Course staff reserve the right to adjust or tailor specific parameters post-submission to ensure final grades are highly representative of design performance and ECSA attribute tracking.
