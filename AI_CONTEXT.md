# AI_CONTEXT.md

## 1. Project Overview & Context
* **Course/Project:** University of Cape Town (UCT) Micromouse Design Project (Course Codes: EEE3097S / EEE3098S / EEE3099S).
* **Role:** Course Convenor (2026 Academic Year Rollout).
* **Core Philosophy Change:** For 2026, the assignment centers around a high-level **Software Paradigm Design Choice**. Students must implement, document, and defend their selected software framework within their engineering portfolios to satisfy ECSA Graduate Attribute 3 (Engineering Design).

---

## 2. The Two Student Paradigms (The Student's Choice)
Students must select and implement **one** of the following two development tracks:

### Track 1: Classic Model-Based Design (MBD) Track
* **Workflow:** Students design their navigation state-machines, wall-following trajectory filters, and high-frequency PID controllers entirely within **MATLAB/Simulink**.
* **Hardware Execution:** Simulink Coder compiles these visual blocks into optimized bare-metal C code. This code is cross-compiled via the GNU ARM toolchain and flashed directly onto the hardware.
* **Simulation/Grading:** Code executes natively inside an isolated external instance, communicating via network sockets back into the central autograding master engine.

### Track 2: On-Chip Low-Level Scripting Track (MicroPython + C Kernel Proxy)
* **Workflow:** Students write their high-frequency closed-loop control strategies (e.g., motor speed sync, encoder tracking, IMU yaw correction, wall-following PIDs) and high-level maze-solving algorithms entirely in **MicroPython** executing directly on the mouse.
* **Hardware Execution:** An on-chip co-processing scheme is used. MicroPython runs the high-frequency control loop (~100 Hz). It passes atomic hardware actuation commands (raw PWM velocities like `micromouse.set_pwm(45, 55)`) and fetches raw data frames through ultra-low-latency native C module bindings connected directly to a pre-compiled C Hardware Proxy Kernel.
* **Simulation/Grading:** Desktop Python executes the identical script on a host computer. A local wrapper library maps the low-level atomic API commands and sensory queries through an IPC TCP/IP loopback socket into the legacy Simulink autograder backend.

---

## 3. Existing Legacy Infrastructure Baseline
The template hardware baseline stems from Jesse's custom **STMicroelectronics STM32L476VETx** configuration:
* **Hardware Drivers Available:** `Motors.c/h` (PWM output & encoder counting) , `ADCs.c/h` (Analog IR distance walls) , `VL53L1X.c/h` (I2C long-range Time-of-Flight laser) , and `IMU.c/h` (Gyroscope orientation tracking).
* **Legacy Simulation Communication:** Simulink simulates virtual maze mechanics , pushes synthetic sensor data down via an ASCII "JSON-lite" key-value format parsed with static `sscanf()` , and reads back target control intents at $100\text{ Hz}$.

---

## 4. Co-Simulation & Dual-Evaluation Architecture
To completely eliminate visual block insertion errors (such as students visually reordering Inport/Outport indices and breaking harness connections), **all programmatic block manipulation is removed**. 

The Simulink Autograder engine behaves exclusively as a **TCP/IP Local Loopback Socket Server (`localhost:8000`)**. The simulation loop is split across two variant paths managed by a **Variant Subsystem Block**:

```text
+---------------------------------------------------------------------------------+
|                        YOUR SIMULINK AUTOGRADER ENGINE                          |
|    - Always acts as a Local Network Socket Server (localhost:8000)              |
|    - Streams JSON Sensor Strings  <===>  Reads JSON Actuator Strings            |
+---------------------------------------------------------------------------------+
^
| (Deterministic TCP/IP Socket Stream)
v
+-------------------------------+-------------------------------+
|                                                               |
v (Track 1: Simulink Choice)                                    v (Track 2: Python Choice)
+-------------------------------+                               +-------------------------------+
|      STANDALONE MATLAB APP    |                               |     STANDALONE PYTHON APP     |
| - Student's compiled model    |                               | - Student's main.py script    |
|   runs as an isolated instance|                               |   runs natively in Python     |
| - Uses TCP Client blocks to   |                               | - Uses native socket library  |
|   exchange JSON data strings  |                               |   to exchange JSON data string|
+-------------------------------+                               +-------------------------------+
```

* **Track 1 Evaluation:** The grading engine runs the native compiled model directly inside the kinematic simulator environment.
* **Track 2 Evaluation:** The grading engine replaces the student block with standard Instrument Control Toolbox **TCP/IP Send** and **TCP/IP Receive** blocks. The autograder fires up the student's `.py` script as a background process. Simulink sends virtual sensor parameters to `localhost:8000`, the Python script handles them using standard dictionary maps (`json.loads()`), updates its maze matrices, and replies with a macro directive command string.

---

## 5. MicroPython-to-C Hardware Kernel Architecture

```text
+---------------------------------------------------------------------------------+
|                                 STM32L476 SILICON                               |
+---------------------------------------------------------------------------------+
|  [USERLAND LAYER]                                                               |
|  MicroPython Runtime Environment (~1 Hz to 5 Hz Macro Decision-Making Loop)     |
|  - Tracks 16x16 Grid Array Matrices, Exploration Logic, and Routing Path        |
|  - Invokes Native C Module Bindings (e.g., micromouse.move_forward(180))        |
+---------------------------------------------------------------------------------+
|
|  On-Chip Inter-Process Messaging
|  Latency: < 1 microsecond (Direct SRAM Pointers)
v
+---------------------------------------------------------------------------------+
|  [HARDWARE ABSURDITY KERNEL]                                                    |
|  Pre-Compiled Bare-Metal C Engine (Deterministic 1 kHz Interrupt Loops)         |
|  - Executes high-frequency Real-Time Motor PID Cascades & Trajectory Tracking   |
|  - Integrates IMU Gyro Angular Velocity over time to compute strict Heading     |
|  - Directly wraps Jesse's legacy files (Motors.c, IMU.c, VL53L0X.c)             |
+---------------------------------------------------------------------------------+
```

### Safety & Stability Isolation
High-frequency physical control operations (e.g., sample-by-sample gyro integration, motor current correction, and PID adjustments) are **explicitly managed by the C Kernel** inside deterministic $1\text{ kHz}$ hardware interrupts. If MicroPython undergoes a garbage collection pause or a slow algorithmic processing step, the robot will **not** fly out of control; the C kernel safely maintains tracking control while waiting for the next macro instruction.

### The Handshake & Synchronization Rule
Compound operations like turning $90^\circ$ or moving forward one cell length ($180\text{ mm}$) are designed as blocking actions. Calling `micromouse.move_forward(180)` in MicroPython triggers the underlying kernel handler, which puts the MicroPython execution thread to sleep/blocked. The C kernel drives the motors, tracks the encoders at a high frequency, and only releases control back to the MicroPython engine by returning a synchronization token (`\nOK\n` or direct function return) **after the physical movement settles completely**.

---

## 6. Target Implementation Tasks for the AI Collaborator
Please assist with implementing the following building blocks:

1.  **Task 1 (MicroPython C Module Bindings):** Write the C wrapper boilerplate exposing Jesse's low-level variables as a native MicroPython C module (`micromouse`), mapping high-level Python commands to internal kernel functions.
2.  **Task 2 (Co-Simulation Python Wrapper):** Write the desktop-side `micromouse.py` fallback module that implements the exact same API signatures, but packages the commands into TCP network frames communicating over a socket interface to port 8000 for Simulink autograding.
3.  **Task 3 (The C Kernel Blocking Control Loops):** Write the C code for `kernel_move_straight(int16_t mm)` and `kernel_execute_turn(int16_t degrees)` that safely loops on top of Jesse's non-blocking drivers, integrating the IMU data and handling the blocking synchronization mechanism cleanly.