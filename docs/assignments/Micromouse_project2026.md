# Micro-mouse Project: EEE3097S, EEE3098S, EEE3099S (2026 Revised Brief)

*This document details the project structure, milestones, learning onramps, and ECSA Graduate Attribute 3 (Design) requirements for the 2026 academic year.*

---

## 1. Project Overview & Motivation

The objective of this course is to systematically design, build, and test a software control strategy to enable a physical differential-drive micro-mouse to autonomously map a maze and subsequently navigate from a starting point to a designated target cell as fast as possible.

* **For Motivation, watch the world-record runs:** [Micromouse World Record Motivation](https://www.youtube.com/watch?v=ZMQbHMgK2rw)

---

## 2. Learning Onramps & Resources

Depending on your chosen development path, complete the following onramps before beginning:

### Simulation & Control Onramps (For Simulink Path)

* **Course 1:** [MATLAB Onramp](https://matlabacademy.mathworks.com/details/matlab-onramp/gettingstarted)
* **Course 2:** [Simulink Onramp](https://matlabacademy.mathworks.com/details/simulink-onramp/simulink)
* **Course 3:** [Stateflow Onramp](https://matlabacademy.mathworks.com/details/stateflow-onramp/stateflow)

### Python & Microcontroller Onramps (For Python Path)

* [MicroPython Documentation](https://docs.micropython.org/)
* [PikaScript Bare-Metal Python Engine Documentation](https://github.com/pikascript/pikascript)

### Repository Structure & Guide Index

To navigate the codebase, understand the primary directories of this repository and their roles:

*   **[`docs/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs)**: Reference guides, hardware specifications, calibration procedures, and project briefs.
*   **[`python/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python)**: Target directory for the Python development track. Contains milestone templates and the student-facing `uct_mouse` wrapper module.
*   **[`matlab/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/matlab)**: Target directory for the Simulink development track. Contains visual models, workspace setups, and helper scripts.
*   **[`src/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/src)**: The core microcontroller codebase. Includes the low-level C Kernel (`src/kernel/`), MicroPython board wrappers (`src/micropython/`), and PikaScript engines (`src/pikascript/`).
*   **[`tools/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/tools)**: Diagnostic and testing utilities, including the local virtual physics simulator testbed.
*   **[`external/`](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/external)**: Git submodules for embedded engines (e.g., MicroPython) and hardware templates.

#### Key Markdown Guides

For detailed guidance when performing specific tasks, refer to these guides in the `docs/` folder:

*   **Project Workflow & Setup:** [UCT Micromouse Student Workflow Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md)
    *   *Purpose:* Start here. Explains how to install dependencies, run the virtual co-simulation, compile your code, and flash it to the physical Nucleo microcontroller.
*   **Simulink Development:** [Simulink Development & Autograding Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/simulink_guide.md)
    *   *Purpose:* Guides you through configuring the MATLAB search path, utilizing C-Caller blocks, running interactive desktop simulations, and code compilation via Embedded Coder.
*   **Kernel & API Reference:** [Micromouse Kernel & API Developer Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/kernel_api_guide.md)
    *   *Purpose:* Explains the polymorphic architecture, Python API function definitions, and the telemetry protocol schemas.
*   **Hardware Setup & Calibration:** [Hardware Setup & Calibration Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/hardware_setup.md)
    *   *Purpose:* Covers physical motor polarity correction, Watchdog safety limits, and resolving clock rate/baud serial synchronization errors.

### Core References

* **Equations of Motion:** [Equations of Motion for Differential Drive Robots](https://www.youtube.com/playlist?list=PLAJu9N587O-G_L416r9rK5P1h55V6J7S0)
* **Control Theory:** [Control of Differential Drive Robots for Path Traversal](https://www.youtube.com/playlist?list=PLAJu9N587O-G_L416r9rK5P1h55V6J7S0)

---

## 3. Repositories

You will need code from both of the following repositories to develop the required software:

1. **Primary Workspace & Simulation Host:** [https://github.com/nicollsf/UCT-Micromouse](https://github.com/nicollsf/UCT-Micromouse)
2. **STM32 Nucleo Microcontroller Kernel Templates:** [https://github.com/JesseJabezArendse/MicroMouseTemplate](https://github.com/JesseJabezArendse/MicroMouseTemplate)

To clone this repository with all required submodules, execute:

```bash
git clone --recursive https://github.com/nicollsf/UCT-Micromouse.git
```

If you have already cloned the repository without the submodules, initialize them using:

```bash
git submodule update --init --recursive
```

---

## 4. Development Architecture (Dual-Path)

The 2026 platform implements a polymorphic three-tier architecture (detailed in [Kernel & API Developer Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/kernel_api_guide.md)). This allows you to run the exact same algorithm code in virtual co-simulation and on the actual STM32 physical mouse without modifying your code.

You may choose to develop your solution using either:

* **Option A: Python (MicroPython / PikaScript):** Write high-level scripts targeting the [uct_mouse](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python/uct_mouse.py) wrapper API.
* **Option B: MATLAB / Simulink / Stateflow:** Model control systems visually using the `StudentTemplate.slx` workspace and use the Embedded Coder to compile it to the STM32 microcontroller.

---

### 5. Course Submissions & Assessment Structure

To pass the course, students are required to make **five primary submissions** that document their practical progress and provide evidence for ECSA accreditation:

1.  **Submission 1: Milestone 1 (The Square Run) Code & Physical Evidence**
    *   **Deliverables:** Student algorithm source file (`main.py` or `.slx` model) and physical run evidence (serial log from the physical mouse + video recording of the mouse traversing a 1.0m x 1.0m square).
2.  **Submission 2: Milestone 2 (Maze Exploration) Code & Physical Evidence**
    *   **Deliverables:** Student algorithm source file and physical run evidence (serial log + video recording of the physical mouse autonomously exploring and mapping a maze layout).
3.  **Submission 3: Milestone 3 (Final Maze Solving) Code & Validation**
    *   **Deliverables:** Final algorithm source file. This submission is evaluated in simulation (completely solving the maze under stress testing) and validated via a final live physical demonstration of the mouse mapping and traversing the maze as fast as possible.
4.  **Submission 4: Graduate Attribute (GA3) Design Report 1**
    *   **Deliverables:** A formal engineering design report (using the template [EEE3097S_designreport.docx](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assignments/EEE3097S_designreport.docx)) documenting a structured design process for a chosen subsystem or algorithm.
5.  **Submission 5: Graduate Attribute (GA3) Design Report 2**
    *   **Deliverables:** A second formal design report documenting a different, distinct subsystem or design task of the student's choosing.

> [!NOTE]
> **GA Report Resubmissions (Catch-up):**
> If either of your first two GA reports fails to provide sufficient evidence of meeting the ECSA GA3 Design Attribute, a third resubmission opportunity is provided to address feedback and demonstrate proficiency.

### Simulation Stress-Testing
To ensure grading remains scalable and objective, the autograder runs your submission against parameter perturbations to verify you are using **active feedback control** (speed matching and gyro heading alignment) rather than hardcoded open-loop delays. The simulated environment will introduce:
*   **Motor Asymmetry:** Left/right motor gain offsets (up to $\pm 10\%$).
*   **Wheel Slip / Traction Loss:** Realistic wheel slippage to penalize pure time/encoder dead reckoning.

---

## 6. Practical Milestones

### Milestone 1: Dead Reckoning & Closed-Loop Path Traversal (The Square Run)
*   **Task:** The mouse must drive a closed loop: drive 1.0m straight, turn 90° right, and repeat this 4 times to form a 1.0m x 1.0m square, then stop.
*   **Assessment:** Your code is evaluated in co-simulation under motor asymmetry and wheel slip perturbations to assess tracking robustness. Physical validation requires a video demonstrating the physical mouse executing the square run on the lab floor, accompanied by its serial sensor log.

### Milestone 2: Robust Maze Exploration
*   **Task:** Navigate a virtual mouse to explore a 4x6 grid maze. Your algorithm must map as many cells as possible and attempt to return to the starting cell.
*   **Assessment:** Evaluated in simulation under stress testing. Physical validation requires a video demonstrating the physical mouse autonomously exploring and mapping a maze layout, accompanied by its serial sensor log.

### Milestone 3: Final Maze Solving
*   **Task:** Completely solve the maze. The mouse must map the layout, compute the shortest path, and run from the start cell to the target cell.
*   **Assessment:** Evaluated in simulation under stress testing, followed by a final live hardware demonstration in the physical maze.

---

## 7. Graduate Attribute 3 (Design) Reports

For each of your GA3 Design Reports, you must identify and design a solution to a distinct engineering design challenge of your choosing. You must define its criteria/constraints, implement your proposed solution, and evaluate its performance.

> [!NOTE]
> While historically scheduled alongside milestones, GA reports are independent written reports. They do **not** have to be directly related to the milestone tasks, though students may choose to write their report on a subsystem developed for the milestones.

### ECSA Graduate Attribute 3 (Design) Assessment Criteria
To satisfy ECSA accreditation standards, your design reports must provide clear, documented evidence of a structured engineering design process mapping to the following criteria:

*   **Assessment Criterion 3.1: Problem Definition & Constraints**
    *   *Scope:* Formulate a clear design brief. Specify the quantitative design criteria (desired features, functionality, target performance parameters) and physical/computational constraints (e.g., RAM/CPU limits on STM32, sensor resolution, motor saturation, safety distances).
*   **Assessment Criterion 3.2: Generation & Evaluation of Alternative Solutions**
    *   *Scope:* Identify and document at least two alternative engineering approaches or algorithms to solve the problem. Evaluate these alternatives against your criteria and constraints, and select the preferred approach based on structured trade-offs.
*   **Assessment Criterion 3.3: Detailed Design & Mathematical Modeling (First-Principles)**
    *   *Scope:* Perform the detailed design, including mathematical modeling, algorithm state-flows, or control-law formulations from first-principles engineering science. Show the equations or logical models governing your design.
*   **Assessment Criterion 3.4: Implementation & Experimental Verification**
    *   *Scope:* Translate your design into a functional reality (Python code or Simulink model). Test and verify the design in the simulated and/or physical environment under realistic perturbations (e.g., slip, asymmetry, noise), documenting performance against your target criteria.
*   **Assessment Criterion 3.5: Design Evaluation & Discussion**
    *   *Scope:* Evaluate the final solution against the original brief. Discuss design limitations, failures, and deviations from the theoretical model, drawing engineering conclusions based on test results.

### Example GA3 Design Project Topics
The topics below are **illustrative examples** of appropriate projects. You are **not required** to select your project from this list. You are highly encouraged to identify and propose your own design challenges that demonstrate Graduate Attribute 3 (Design) criteria.

To help you understand exactly what evidence is required in your report, each example below is mapped directly to the ECSA GA3 rubric sections. Even if you choose your own topic, it must be developed and documented to this level of detail.

#### Category A: Control, Estimation & Kinematics

1.  **Robust Odometry & Gyro-Encoder Sensor Fusion:** Design a discrete sensor-fusion estimator (e.g., Complementary Filter or Kalman Filter) to combine wheel encoder tick counts and gyro yaw rates.
    *   **Criteria & Constraints (3.1):** Define target yaw/position estimation accuracy (e.g., heading error < 1° after 10m traversal) and physical/computational limits (e.g., filter runtime must fit within the 10ms CPU control tick).
    *   **Alternative Solutions (3.2):** Compare and contrast at least two fusion approaches (e.g., a simple complementary filter vs. a discrete Kalman filter) against baseline raw-encoder dead reckoning.
    *   **First-Principles Modeling (3.3):** Formulate the differential-drive kinematic state space equations, coordinate transformations, and sensor noise covariance models.
    *   **Implementation & Verification (3.4/3.5):** Implement the filter in code/Simulink and test its tracking robustness under simulated wheel slip and gyro drift perturbations, comparing estimated vs. true path.
2.  **Dual-Wheel Closed-Loop Speed Controller (PID):** Design and tune a discrete PID feedback controller to regulate left/right wheel speeds independently.
    *   **Criteria & Constraints (3.1):** Define quantitative performance targets (e.g., overshoot < 5%, settling time < 0.1s) and hardware limits (e.g., motor driver PWM saturation limits, battery voltage drop down to 3.0V).
    *   **Alternative Solutions (3.2):** Compare at least two controller structures (e.g., a standard discrete-time PID controller vs. a Feedforward-augmented PID controller vs. a Lead-Lag compensator).
    *   **First-Principles Modeling (3.3):** Derive the differential equations/transfer functions modeling the DC motor electrical and mechanical dynamics, and apply the z-transform to discretize the control law.
    *   **Implementation & Verification (3.4/3.5):** Implement the controller and evaluate performance under asymmetrical motor gains and variable surface friction in simulation and hardware step-response trials.
3.  **Coordinated High-Speed Cornering Profile (Trajectory Tracking):** Design a trajectory generator and feedback controller enabling the mouse to turn 90° smoothly without stopping.
    *   **Criteria & Constraints (3.1):** Define the maximum permissible lateral error (e.g., < 2 cm) and physical traction constraints (preventing sliding on lab floor).
    *   **Alternative Solutions (3.2):** Evaluate at least two geometric path designs (e.g., a constant-radius arc vs. a clothoid spiral vs. a Bézier curve trajectory) to determine their impact on wheel acceleration.
    *   **First-Principles Modeling (3.3):** Model the vehicle's dynamics during turning, including lateral slip limits, centrifugal force ($F_c = m v^2 / R$), and maximum grip boundary based on tire-floor friction coefficient.
    *   **Implementation & Verification (3.4/3.5):** Code the trajectory tracker and verify it against tracking errors and traction limits when entering the turn at various speeds under simulated traction loss.
4.  **Active Centering and Wall Alignment via ToF Feedback:** Design an active alignment controller keeping the mouse centered in corridors and aligned parallel to walls.
    *   **Criteria & Constraints (3.1):** Define target alignment settling distance (e.g., stable centering within 0.5m of entry) and handle ToF sensor noise and range limitations.
    *   **Alternative Solutions (3.2):** Compare two feedback strategies (e.g., a state-space regulator with state feedback vs. a multi-loop PID controller taking distance and differential distance).
    *   **First-Principles Modeling (3.3):** Develop the geometric/kinematic model mapping left/right distance measurements to the mouse's lateral displacement ($d_y$) and heading angle error ($\theta_e$) relative to the corridor axis.
    *   **Implementation & Verification (3.4/3.5):** Test the controller's stability and speed of alignment under simulated corridor discontinuities (e.g., sudden wall openings/junctions) and distance sensor noise.
5.  **Reflectance-Based Odometry Correction (Line Sensors):** Design an algorithm utilizing downward-facing reflectance/line sensors (exposed via the `get_line_sensors()` API) to correct cumulative dead-reckoning drift.
    *   **Criteria & Constraints (3.1):** Define the maximum allowed cumulative position uncertainty before correction (e.g., < 5 cm per cell grid) and reflectance threshold parameters.
    *   **Alternative Solutions (3.2):** Compare a threshold-triggered absolute coordinate reset approach vs. a state estimation correction routine (e.g., Extended Kalman Filter measurement updates using floor grid markings).
    *   **First-Principles Modeling (3.3):** Model the spatial reflectance profile of the maze floor (white grid lines on dark background) and formulate the mathematical correction updates of the position coordinate vector when sensors trip.
    *   **Implementation & Verification (3.4/3.5):** Implement the correction logic and verify coordinate convergence in simulation under high wheel slip and cumulative drift conditions.
6.  **Offline Trajectory Reconstruction & Extended Kalman Smoothing:** Collect a full sensor telemetry log from a physical maze run and design an offline post-processing smoothing algorithm (e.g., a Rauch-Tung-Striebel / Extended Kalman Smoother).
    *   **Criteria & Constraints (3.1):** Define target path reconstruction resolution and off-board computation limits (e.g., execution time constraints on PC log processors).
    *   **Alternative Solutions (3.2):** Compare forward-only filtering (standard EKF) against forward-backward smoothing (RTS Smoother) in reconstructing the actual traversed coordinates.
    *   **First-Principles Modeling (3.3):** Formulate the state-space equations for a differential-drive robot, the non-linear measurement models for gyro/encoder logs, and the smoothing recurrence relations.
    *   **Implementation & Verification (3.4/3.5):** Verify the reconstructed path against simulated ground truth trajectory and hardware log data, analyzing performance under random noise and encoder ticks corruption.
7.  **Reinforcement Learning (RL) for Kinematic Control:** Train an RL agent (e.g., using Q-learning or policy gradients) to control motor PWM signals directly.
    *   **Criteria & Constraints (3.1):** Define limits on learning epochs, safety constraints (preventing motor saturation and crash during exploration), and RAM/CPU footprints for target microcontroller execution.
    *   **Alternative Solutions (3.2):** Compare a classical linear feedback controller (e.g., PID) against the learned policy in terms of speed of traversal and tracking error.
    *   **First-Principles Modeling (3.3):** Formulate the Markov Decision Process (MDP) state-space representation, design the reward function (penalizing lateral error and slip, rewarding forward speed), and choose regularized model constraints.
    *   **Implementation & Verification (3.4/3.5):** Train the agent in simulation and test its robustness against changes in surface friction and motor response delays to evaluate policy stability.

#### Category B: Software Systems & Interface Engineering (Blockly / API Track)

8.  **High-Level Safety Wrapper API (`uct_blocks.py`):** Design a software class library translating user command blocks (like `move_cells(n)`) into safe hardware-level actions.
    *   **Criteria & Constraints (3.1):** Define safety response latency (e.g., obstacle detection and emergency stop command issued within 20ms) and software footprint constraints (e.g., < 2KB RAM).
    *   **Alternative Solutions (3.2):** Compare a synchronous polling-based safety loop vs. an asynchronous, interrupt-driven safety monitoring task.
    *   **First-Principles Modeling (3.3):** Formulate the software system architecture, state-transition diagrams for safety overrides, and worst-case execution time (WCET) models.
    *   **Implementation & Verification (3.4/3.5):** Implement the wrapper on the mouse, simulating sudden obstacle insertion at maximum speed to verify it triggers emergency braking within the 3cm safety zone.
9.  **Visual Programming Language and Code Generator (Blockly Interface):** Design a custom Blockly block library and its corresponding Python code generator for programming maze-solving logic.
    *   **Criteria & Constraints (3.1):** Define safety properties (e.g., generated code must never enter infinite blocking loops, MCU heap allocation must remain under 32KB).
    *   **Alternative Solutions (3.2):** Compare structured, loop-protected visual blocks (e.g., with built-in time-out loops) against generic freeform control blocks.
    *   **First-Principles Modeling (3.3):** Model the grammar/syntax translation rules, abstract syntax tree (AST) conversion mappings, and runtime recursion depth constraints.
    *   **Implementation & Verification (3.4/3.5):** Test the generator by feeding diverse block configurations and verifying that the generated Python script runs on the bare-metal interpreter without memory leaks or crashes.
10. **Autonomous Multi-Phase Calibration and System Identification Utility:** Design an on-mouse interactive calibration script estimating the physical parameters of the specific chassis.
    *   **Criteria & Constraints (3.1):** Define target parameter accuracy (e.g., gyro drift bias computed within $\pm 0.05$ deg/s, motor gain within $\pm 2\%$) and calibration time limits (e.g., total routine < 15 seconds).
    *   **Alternative Solutions (3.2):** Evaluate at least two parameter identification methods (e.g., standard least-squares regression vs. recursive parameter estimation).
    *   **First-Principles Modeling (3.3):** Derivation of system identification equations: mapping input motor PWM to angular wheel speed, extracting gyro bias via stationary integration, and calculating wheel diameter from linear run trials.
    *   **Implementation & Verification (3.4/3.5):** Execute the utility on the simulated or physical mouse and verify that calibration parameters converge to true physical values, improving subsequent trajectory tracking accuracy.
11. **Baud-Rate Calibration and Synchronization State-Machine (Clock Lottery):** Design a state-machine dynamically detecting UART communication corruption and synchronization errors on startup.
    *   **Criteria & Constraints (3.1):** Define startup synchronization time (e.g., establish stable channel within 1 second of boot) and allowable bit error rate limits.
    *   **Alternative Solutions (3.2):** Compare a blind frequency sweep handshake protocol against an adaptive baud-rate auto-baud detection scheme utilizing start bit timing analysis.
    *   **First-Principles Modeling (3.3):** Derive timing equations and error margins for clock drift, framing tolerances, and UART signal jitter. Model the synchronization system as a Finite State Machine (FSM).
    *   **Implementation & Verification (3.4/3.5):** Implement the FSM on the STM32 and simulate severe clock mismatches ($\pm 15\%$) to verify communication is reliably established without frame drops.
12. **Robust Complex "Atomic" Visual Block:** Design a single custom visual programming block (e.g., "traverse_corridor_safely") encapsulating complex multi-sensor closed-loop logic.
    *   **Criteria & Constraints (3.1):** Define limits on execution latency (e.g. control output calculated within 5ms) and the range of obstacle shapes it must handle.
    *   **Alternative Solutions (3.2):** Compare a single monolithic state machine vs. a modular, hierarchically nested state-machine (using Stateflow or state charts) separating wall alignment, forward speed control, and junction detection.
    *   **First-Principles Modeling (3.3):** Formulate the logical rules governing transition events (e.g., wall presence/absence thresholds) and the kinematics of centering during corridor traversal.
    *   **Implementation & Verification (3.4/3.5):** Map the block to student code and verify path stability under sensor failures (e.g. simulating a blocked or dead ToF sensor).
13. **Asynchronous Multiplexed Wireless Telemetry Protocol (ESP32 / Radio Module):** Design a wireless communication protocol and a PC dashboard interface using a serial radio module.
    *   **Criteria & Constraints (3.1):** Define packet latency constraints (e.g., telemetry latency < 50ms at 115200 baud), buffer size limits, and checksum error tolerance.
    *   **Alternative Solutions (3.2):** Evaluate alternative serialization schemes (e.g., lightweight binary framing with COBS encoding vs. raw JSON strings) to balance payload size and CPU processing overhead.
    *   **First-Principles Modeling (3.3):** Formulate the data link layer state transitions, checksum math (e.g. CRC16), and compute bandwidth utilization and channel overhead equations.
    *   **Implementation & Verification (3.4/3.5):** Implement the protocol on the STM32 and verify that streaming high-frequency data does not impact the real-time motor control task or lead to buffer overflow under simulated packet dropouts.

---

## 8. Final Maze-Solving Competition

At the end of the course, students are invited to enter a live maze-solving competition with their physical micro-mouse. If a student's mouse successfully explores, maps, and executes a high-speed run from the starting cell to the target cell, they will be awarded **100% for the practical component of the course**. This reflects the system synthesis and validation necessary to achieve full, real-world autonomy.
