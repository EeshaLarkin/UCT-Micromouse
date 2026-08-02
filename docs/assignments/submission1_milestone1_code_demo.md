# EEE3097/8/9S Micromouse 2026: Submission 1
## Milestone 1 Code & Demo (25% of Course Mark)

---

### 1. Objective
Design and implement a closed-loop controller that guides your Micromouse robot to traverse a perfect **1.0m x 1.0m square** on the floor and stop autonomously. Your design must use closed-loop feedback (such as gyroscope yaw heading alignment and quadrature encoder distances) to remain robust against traction loss, slip, and motor asymmetries.

#### **Specific Learning Objectives:**
* Configure and read quadrature wheel encoders to track linear distance.
* Interface with the MPU6050 IMU gyroscope and integrate angular rate to track heading.
* Formulate a Proportional (P) or PID controller to synchronize wheel velocities and steer the mouse differentially.
* Implement a finite state machine (FSM) to transition between straight trajectories and spin-in-place turns.

---

### 2. Step-by-Step Implementation Guide
* **Sensor Calibration:** Write a test script to verify that pushing the mouse forward increases both encoder counts symmetrically, and that manual rotation returns correct yaw scale factors.
* **Speed Synchronization:** Adjust left/right motor PWM dynamically so both wheels rotate at the same linear velocity.
* **Heading Correction:** Add integrated gyro yaw to the feedback loop to correct for drift and bumps.
* **Spin-in-Place:** Implement a precise 90° right turn using differential spin and a settling window.
* **State Machine:** Sequence: Drive 1m $\rightarrow$ Turn 90° $\rightarrow$ Repeat 4x $\rightarrow$ Stop. The mouse must halt autonomously.

---

### 3. Deliverables (Gradescope Submission)
Run the packaging command from your repository root:
```bash
python tools/package_submission.py --task milestone1 --src workspace/task1_square/
```
Upload the resulting **`submission_milestone1.zip`** AND your **`run_video.mp4`** separately to Gradescope (Gradescope allows you to drag-and-drop both files into the submission portal together).

The submission consists of:
1.  **Your ZIP Package (`submission_milestone1.zip`):**
    *   **Your Controller Code:** Automatically compiled and zipped from your workspace directory (includes `main.py` and any subfolders/libraries recursively).
    *   **Physical Telemetry Log (`run_log.jsonl`):** Automatically detected by the packager tool from your project directory (no need to copy it manually).
2.  **Your Physical Run Video (`run_video.mp4`):**
    *   Uploaded as a **separate file** alongside your ZIP. The video must start with a **3-second close-up of your Student Card** followed by the uncut square run.

---

### 4. Code & Log Check (Anti-Cheat)
* **Code Match Check:** The autograder compiles/hashes your submitted code and verifies that it matches the FNV-1a `"hash"` checksum in your telemetry header. Mismatches will reject the submission.
* **Hardware ID Check:** Microcontroller Device UIDs are tracked. Shared logs under different student accounts will trigger a plagiarism audit.

---

### 5. Evaluation Criteria & Grading Rubric
Your Gradescope submission is evaluated across two parts:

*   **Part A: Autograded Co-Simulation Trajectory (60% of Milestone Mark):**
    Your controller is tested in a virtual testbed under randomized perturbations ($\pm 10\%$ motor gain asymmetries and $8\%$ wheel slip). The simulation runs up to a **45-second limit** and automatically completes when the mouse is detected to be **stationary for 3.0 seconds** after initial movement.
    
    The autograder score is calculated out of 100 points as follows:
    *   **Progression Score (60 points max):** The mouse earns **20 points for each corner successfully reached** in sequential clockwise (right-turning) order:
        *   Corner 1 (1.0m straight): **20 pts**
        *   Corner 2 (first 90° turn and 1.0m leg): **40 pts**
        *   Corner 3 (second 90° turn and 1.0m leg): **60 pts**
    *   **Return to Start Bonus (20 points):** Awarded if the mouse successfully completes all four legs and returns/stops within a **reasonable 30 cm radius** of the starting coordinates.
    *   **Return Accuracy Points (20 points max):** If the return bonus is earned, the final return error ($d_e$) is graded on a continuous scale:
        *   $d_e \le 5\text{ cm}$: Full **20 pts** (Perfect feedback control)
        *   $5\text{ cm} < d_e \le 15\text{ cm}$: Scales linearly from **20 down to 10 pts**
        *   $15\text{ cm} < d_e \le 30\text{ cm}$: Scales linearly from **10 down to 0 pts**
    *   **Applied Penalties:**
        *   **Timeout ($-10$ points):** Applied if the controller fails to stop within the 45-second limit.
        *   *Collision Note:* Contacting a wall halts the simulation immediately, naturally capping your score based only on the corners completed prior to the crash. No additional numerical collision penalties are subtracted.

*   **Part B: Physical Run Verification (30% of Milestone Mark):**
    Tutors will evaluate your submitted physical demonstration video (`run_video.mp4`) and verify hardware control performance. Marks are awarded for smooth acceleration/deceleration transitions, correct turn alignments, and successful autonomous execution on real floor surfaces without manual intervention or drifting out-of-bounds.

*   **Part C: Submission Compliance (10% of Milestone Mark):**
    Evaluated by tutors on instruction compliance:
    *   **All Files Included (5%):** Correct zipping of source code workspace and valid FNV-1a checksum matched physical telemetry log file (`run_log.jsonl`).
    *   **Student Card Close-up (5%):** The physical demo video begins with a clear, readable 3-second close-up of your Student Card.

---

> [!NOTE]
> **Grading Adaptation Policy:** The grading thresholds, coefficients, and parameters detailed above serve as baseline targets. Course staff reserve the right to adjust or tailor specific parameters post-submission to ensure final grades are highly representative of design performance and ECSA attribute tracking.
