# EEE3097/8/9S Micromouse 2026: Milestone 3 Instructions
## Final Maze Solving (Speed Run)

---

### 1. Objective
Implement a high-speed path planning and navigation algorithm for your Micromouse. The mouse must first explore the maze layout to find the shortest path from the start cell to the target cell, compute the optimal routing path, and then execute a high-speed "speed run" to the target.

#### **Specific Learning Objectives:**
* Implement shortest-path planning algorithms (e.g., Floodfill, Dijkstra, or Breadth-First Search) to compute optimal routes through a mapped wall grid.
* Design velocity profiles (acceleration, cruise speed, deceleration) to transition between straightaways and turns.
* Formulate trajectory tracking controllers for high-speed straight-line runs.
* Optimize cornering maneuvers (smooth turns without coming to a complete stop).

---

### 2. Step-by-Step Implementation Guide

#### **Step 1: Shortest Path Computation**
* Write a solver that imports your mapped wall configuration matrix.
* Program it to calculate the minimum number of cell steps from the starting cell $(0,0)$ to the target cell.
* Output this optimal route as a sequence of target cell coordinate steps.

#### **Step 2: Speed Trajectory Generation**
* Rather than stopping at every cell boundary, design a dynamic velocity planner.
* If your path contains consecutive straight cells (e.g. three cells in a straight line), your controller must accelerate the mouse to high speed, cruise, and then decelerate back to turn speed before the next corner.

#### **Step 3: High-Speed Tracking & Stability**
* At high velocities, standard feedback loops can oscillate. Tune your gyro heading and wall-centering feedback gains to maintain stability at speeds $> 0.5\text{ m/s}$.
* Implement a safety watchdog: if a front wall is detected closer than $8\text{ cm}$ at high speed, trigger emergency braking to prevent catastrophic chassis damage.

#### **Step 4: Speed Run Execution**
* Your controller must sequence the run in two distinct runs:
  1. **Exploration Run:** The mouse maps the maze layout and identifies the target. It returns to $(0,0)$ and stops.
  2. **Speed Run:** The mouse boots, loads the calculated shortest path, and executes a high-speed sprint directly to the target cell, stopping autonomously inside the target.

---

### 3. Deliverables (Gradescope Submission)
To make submission simple and prevent errors, run the following command from your repository root:
```bash
python tools/package_submission.py --task milestone3 --src workspace/task3_maze/
```
This script will perform dynamic verification checks and generate a single **`submission_milestone3.zip`** in your project root. Upload this ZIP directly to Gradescope.

The ZIP package will automatically contain:
1. **Your Solving Code:**
   * **Python track:** All `.py` scripts and custom libraries recursively from your workspace.
   * **Simulink track:** Your model file (`.slx`) and the generated C code-generation directory (`*_ert_rtw/`).
2. **Physical Telemetry Log (`run_log.jsonl`):**
   * The raw telemetry log file of your best physical speed run.
3. **Physical Run Video (`run_video.mp4`):**
   * A single, unedited video demonstrating the physical run.

---

### 4. Video Requirements & Academic Honesty Declaration
To verify that your physical run is authentic, the video must strictly adhere to the following sequence:
1. **Student Card Close-up:** The video **MUST start with a clear, readable close-up of your physical Student Card** for at least 3 seconds (declaring this is your own work).
2. **Setup:** Show the mouse positioned at the starting cell.
3. **Traversals:** Capture the mapping run, the optimal path calculation, and the final high-speed run to the target cell without cuts.

---

### 5. Code & Log Correlation Verification (Anti-Cheat Check)
The autograder uses the log's header to verify authenticity:
* **Hardware ID Check:** The `"uid"` field represents your microcontroller's unique device ID. While this is not registered in advance, the course convenors check the submitted logs for duplicate UIDs. Submitting logs with identical UIDs under different student accounts indicates shared files/hardware runs and will trigger a plagiarism audit.
* **Code Match Check:** The autograder compiles and computes an FNV-1a checksum hash of your submitted code and matches it against the `"hash"` field in your telemetry header. **Mismatches will result in an immediate submission rejection.**

---

### 6. Evaluation Criteria
Your submission will be graded on two parts:

#### A. Co-Simulation Speed & Accuracy (Automated Check)
The autograder will execute your solving code in the visual simulation testbed across multiple randomized maze layouts.
* **Exploration & Pathfinding:** The mouse must correctly calculate the optimal path.
* **Speed Run Execution:** The mouse must execute the run without collisions. Your grade is directly proportional to the traversal speed.

#### B. Physical Validation (Live Demo Check)
You will present your mouse for a live physical evaluation run in the lab maze. The mouse must successfully map and navigate the layout under physical timing limits.
