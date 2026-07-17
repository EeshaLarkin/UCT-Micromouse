# EEE3097/8/9S Micromouse 2026: Milestone 2 Instructions
## Robust Maze Exploration & Mapping

---

### 1. Objective
Design and implement an autonomous exploration algorithm that guides your Micromouse robot to explore and map a **4x6 grid maze**. Your algorithm must navigate the maze, record cell wall configurations, and safely return the mouse to its starting cell.

#### **Specific Learning Objectives:**
* Interface with the three VL53L0X Time-of-Flight (ToF) sensors to measure distances to walls.
* Calibrate distance thresholds to robustly classify wall presence vs. open corridors.
* Implement a grid-based odometry model to track the mouse's current $(x, y)$ cell coordinates and orientation (North, East, South, West).
* Implement a finite state machine or maze explorer algorithm (e.g. wall-follower rules, floodfill, or DFS).
* Maintain a mapping array to log visited cells and wall configurations.
* Plan a path to return autonomously to the starting cell $(0,0)$ once exploration is complete.

---

### 2. Step-by-Step Implementation Guide

#### **Step 1: Front and Side Wall Detection**
* Write a test script to print distance readings from your left, front, and right ToF sensors.
* Record the values when the mouse is positioned in the center of a standard cell (18cm x 18cm) with walls present or absent.
* Formulate threshold logic: if distance to a wall is $< 12\text{ cm}$, classify the wall as present.

#### **Step 2: Grid Coordinate Tracking**
* Your program must track its state in cell coordinates: $(x, y)$ starting at $(0, 0)$, and a heading direction (e.g., $0 = \text{North}$, $1 = \text{East}$, $2 = \text{South}$, $3 = \text{West}$).
* Implement distance tracking using encoders: whenever the mouse travels exactly 18.0cm (one cell length), update the $(x, y)$ coordinates based on your current heading.

#### **Step 3: Exploration Decision Loop**
* Design an exploration algorithm. When the mouse enters a cell:
  1. Halt briefly (optional) and read all three ToF sensors.
  2. Record the detected walls into your map representation.
  3. Evaluate the unvisited adjacent cells.
  4. Select the next cell to explore (using a rule like "follow left wall" or "move to nearest unvisited cell").
  5. Rotate the mouse toward the target cell and drive forward exactly one cell length.

#### **Step 4: Maze Boundary Centering**
* To prevent drift over long exploration runs, use your side ToF sensors to keep the mouse centered. 
* If the left wall is closer than the right wall, adjust motor speeds slightly to steer the mouse back to the center of the corridor.

#### **Step 5: Return to Start**
* Once the maze is explored (or a boundary limits exploration), your algorithm must transition to "Home Return" mode.
* The mouse must navigate back to the starting cell $(0,0)$ and come to a complete stop autonomously.

---

### 3. Deliverables (Gradescope Submission)
To make submission simple and prevent errors, run the following command from your repository root:
```bash
python tools/package_submission.py --task milestone2 --src workspace/task2_maze/
```
This script will perform dynamic verification checks and generate a single **`submission_milestone2.zip`** in your project root. Upload this ZIP directly to Gradescope.

The ZIP package will automatically contain:
1. **Your Exploration Code:**
   * **Python track:** All `.py` scripts and custom libraries recursively from your workspace.
   * **Simulink track:** Your model file (`.slx`) and the generated C code-generation directory (`*_ert_rtw/`).
2. **Physical Telemetry Log (`run_log.jsonl`):**
   * The raw telemetry log file extracted from your physical mouse using `python tools/dump_logs.py`.
3. **Physical Run Video (`run_video.mp4`):**
   * A single, unedited video demonstrating the physical exploration run.

---

### 4. Video Requirements & Academic Honesty Declaration
To verify that your physical run is authentic, the video must strictly adhere to the following sequence:
1. **Student Card Close-up:** The video **MUST start with a clear, readable close-up of your physical Student Card** for at least 3 seconds (declaring this is your own work).
2. **Setup:** Show the mouse positioned at the starting cell of the physical maze.
3. **Exploration:** Capture the complete run without cuts as the mouse explores the walls and returns to the start.

---

### 5. Code & Log Correlation Verification (Anti-Cheat Check)
The autograder uses the log's header to verify authenticity:
* **Hardware ID Check:** The `"uid"` field represents your microcontroller's unique device ID. While this is not registered in advance, the course convenors check the submitted logs for duplicate UIDs. Submitting logs with identical UIDs under different student accounts indicates shared files/hardware runs and will trigger a plagiarism audit.
* **Code Match Check:** The autograder compiles and computes an FNV-1a checksum hash of your submitted code and matches it against the `"hash"` field in your telemetry header. **Mismatches will result in an immediate submission rejection.**

---

### 6. Evaluation Criteria
Your submission will be graded on two parts:

#### A. Visual & Log Audit (Manual/Physical Check)
* **Exploration Rate:** The mouse must successfully map at least 80% of the reachable cells in the maze.
* **Home Return:** The mouse must return and stop autonomously in the starting cell.
* **Log Check:** Telemetry variables must show active wall distance tracking and cell layout logging.

#### B. Co-Simulation Stress Test (Automated Check)
The autograder will execute your exploration code in the visual simulation testbed under motor asymmetries ($\pm 10\%$) and sensor noise perturbations to evaluate mapping robustness.
