# AGENT.md

## 1. Project Overview & Context
* **Course/Project:** University of Cape Town (UCT) Micromouse Design Project (EEE3097S / EEE3098S / EEE3099S).
* **Role:** Course Convenor (2026 Academic Year Rollout).
* **Distribution Paradigm:** Native MATLAB Project Toolbox Add-On deployment.
* **Core Philosophy:** Software paradigm selection serves as an explicit design challenge for ECSA GA 3 / GA 5 compliance tracking.

---

## 2. Micromouse Kernel Design Principles
The Kernel functions as a lean register proxy bridging hardware peripherals to a network socket interface. It contains no closed-loop tracking algorithms or pathfinders.

### A. Communication Infrastructure
1. Communication occurs over network sockets using highly predictable, lightweight textual string packets.
2. Downlink frames actuate motor velocities or update configuration registers; Uplink frames pipe sensory updates back to userland.

### B. Self-Describing Field-Level Encoding
To optimize communication bandwidth without creating brittle global states, the kernel uses self-describing field variants:
1. **Absolute by Default:** Variables are reported as actual total values by default (e.g., `"lenc"` for Left Encoder, `"renc"` for Right Encoder).
2. **Delta Field Variants:** High-frequency accumulators can be configured to transmit as relative deltas. When acting as a delta, the kernel prefixes the JSON key with a `+` (e.g., `"+lenc"`, `"+renc"`).
3. **Full Dump Sync:** A `"sync": 1` request forces the kernel to emit a complete baseline frame using strictly absolute field keys (`"lenc"`, `"renc"`, etc.), allowing the userland application to lock its shadow state perfectly.

### C. Configuration Command Set Protocol
The network parsing interface maps parameters using single-character keys to eliminate messaging overhead:
* **Actuation (`"a"`)**: Direct motor adjustments via arrays, e.g., `{"a":[left_pwm, right_pwm]}`.
* **Poll Request (`"p"`)**: Manual pull indicator string `{"p":1}` to demand an instantaneous sensor payload update.
* **Configuration (`"c"`)**: Explicit properties adjustments:
  * `{"c":{"rate":100}}`: Periodic update stream loop frequency in Hz ($0 = \text{Polled Mode}$).
  * `{"c":{"enc_mode":"d"}}`: Tells the kernel to use the `"+lenc"` and `"+renc"` delta variants for encoder fields. `"a"` reverts to absolute.
  * `{"c":{"sync":1}}`: Forces the kernel to emit an absolute, full baseline frame on the next tick.

---

## 3. Co-Simulation & Autograding Parity
The master Simulink Autograder engine behaves exclusively as a **TCP/IP Local Loopback Socket Server (`localhost:8000`)** streaming the exact same JSON-lite data formats as the physical Tier 1 C Kernel.

### The "Polymorphic" Autograding Pipeline
The autograder evaluates students based on a single, hardware-agnostic Python script (`main.py`). The student does not maintain separate "mouse" and "PC" versions.
1. **Physical Hardware (PikaScript):** When deployed to the mouse, `import uct_mouse` binds directly to the native C-Kernel registers via `.pyi` stubs and the Rust pre-compiler.
2. **Autograder (Simulink/PC):** When submitted to the autograder, the student's script runs on the PC alongside a Desktop Mock version of `uct_mouse.py`. This mock wrapper silently intercepts the student's hardware calls (e.g., `mouse.get_tof_l()`) and translates them into TCP JSON requests to the Simulink virtual maze. The student's logic remains completely untouched, evaluating seamlessly against the virtual environment.

### Simulink Desktop Co-Simulation (Native Tether)
The system also supports native desktop co-simulation directly within MATLAB without requiring a background Python server. 
When a student clicks "Run" in Simulink, the Embedded Coder compiles the `simulink_wrapper.c` file using the Mac/PC's local compiler. An `#ifndef __arm__` directive routes the C-Caller blocks to a native POSIX USB Serial driver that automatically hijacks the `/dev/cu.usbmodem` port and streams JSON to the physical kernel at 100Hz.

Whether a student submits a standalone Simulink binary, a MicroPython script, or a compiled desktop C process, the autograder launches their code as an independent background task, exchanges packets at 100 Hz in a lock-step query-response loop, and utilizes strict 0.5-second socket timeouts to isolate the grading engine from student logic crashes or infinite loops.

---

## 4. Direction Sheet for AI Collaborator
When instructed to build, reference this exact configuration schema:

1. **Phase 1 (Completed):** Establish the Tier 1 C Kernel Bedrock. This includes the `serial_interface.c` network proxy, OLED display overrides, generic key-value application logging, and physical hardware bug fixes.
2. **Phase 2 (Completed):** Build the Tier 2 Simulink/Python Abstraction Layer (`simulink_wrapper.c`). Ensure complete polymorphic execution: the exact same Simulink model must compile natively to the STM32 (`Cmd+B`) and run live over USB tether (`Run` button).
3. **Phase 3 (Completed):** Verify Simulink/Python autograder TCP/IP loopback integration and evaluate Tier 3 userland maze-solving scripts (`milestone1_square.py`, `milestone2_maze.py`).
4. **Phase 4 (Completed):** Implement and document hardware-level quadrature encoder interface hooks in the C-Kernel, and design delta encoding schema to close the physical control loop.


---

## 5. Three-Tier Deployment Architecture
The system is strictly divided into three distinct layers to preserve the kernel's language-agnostic purity while supporting standalone on-mouse execution:

### Tier 1: The Base C Kernel (The Bedrock)
* **Role:** A lean register proxy and JSON-lite network bridge.
* **Rules:** Strictly "dumb". Contains absolutely no closed-loop tracking, PID controllers, or high-level maneuver commands (like `turn_90`). Operates purely on raw PWM inputs and raw sensor outputs.

### Tier 2: The Control Library / Abstraction Layer (`simulink_wrapper.c` / `uct_mouse.py`)
* **Role:** Provides hardware-agnostic functional abstractions (e.g., `simulink_ext_set_motors()`, `simulink_ext_get_tof()`).
* **Rules:** Operates polymorphically. On the physical mouse, it binds natively to C memory registers (Zero-overhead). On the PC (for Desktop Co-Simulation and Autograding), it acts as a proxy, packaging requests into JSON and piping them over USB Serial.

### Tier 3: The User Application (`StudentTemplate.slx` / `main.py`)
* **Role:** The actual maze-solving intelligence.
* **Rules:** Written entirely using the Tier 2 API. Students test this logic on their laptops against the physical mouse (via Green Button Serial tether), then deploy it directly to the silicon (`Cmd+B`), or submit the exact same file to the Autograder.

---

## 6. Hardware Quirks & Known States
* **The 72 MHz / 80 MHz Silicon Lottery:** Due to grey-market silicon or missing HSI factory calibration trims in this specific batch of STM32s, some boards successfully achieve the targeted `80 MHz` PLL clock, while identically flashed sister boards cap out at `72 MHz`.
  * **Impact:** A board running at 72 MHz while programmed for 80 MHz will calculate incorrect UART baud dividers (an 11.1% error), causing the Python dashboard to see garbage hex and hang on connection.
  * **Diagnosis (Baud Sweep):** If the board outputs garbage at 115200 baud, run a serial monitor test at `103680` baud ($115200 \times \frac{72}{80}$). If you see clean telemetry (`{"gyro":...}`), the board clock is running at 72 MHz.
  * **Fix:** The standard firmware strictly targets the healthy `80 MHz` (using `USART1->BRR = 694`). If a specific chassis is confirmed to be a 72 MHz outlier, swap the USART divider in `src/main.c` to `625` and label the board.
* **Bare-Metal Semihosting File I/O Lockup Trap:** Because the microcontroller runs bare-metal without a file system, executing file operations in Python (like `open()` or `with open(...)`) delegates to the C standard library (`libc`).
  * **Impact:** The library attempts to trigger **Semihosting** to perform file I/O on the host machine. This issues an ARM breakpoint instruction (`BKPT 0xAB`), which freezes the microcontroller's CPU immediately. The serial port goes completely dead (0 bytes transmitted).
  * **Fix:** Do not call `open()`, `read()`, or other file system APIs inside Python scripts deployed to the mouse. Default polarity configurations must be hardcoded in code (e.g. `uct_mouse.set_polarity(1, 1)`) rather than read from external text files.
* **Randomized Motor Polarity:** Depending on how the physical DC motor leads were soldered by students/technicians, the chassis might spin backwards or in circles when given a forward command.
  * **Impact:** If students try to flip negative signs in their high-level PID math, their code will fail against the standardized Simulink Autograder.
  * **Fix:** Abstracted at the Tier 1 level. The C Kernel uses `#define POLARITY_L` and `POLARITY_R` (set to `1` or `-1`) in `micromouse_kernel.c` to mathematically normalize the physical wiring before the PWM pulse ever hits the timer register.
* **Left Motor Reverse Casting Bug:** In older ARM GCC toolchains, passing a signed 8-bit negative integer into the standard `<stdlib.h>` `abs()` function mangles the sign bit, causing the left wheel to brake instead of reverse. The C Kernel explicitly bypasses this with a native hardware timer override (`TIM3->CCR4 = -actual_l`).
* **Simulation Double-Stepping Bug (Resolved):** In earlier iterations, calling both `uct_mouse.set_motors()` and `uct_mouse.delay_ms()` within the same loop advanced the physics simulator time step twice per loop.
  * **Impact:** The mouse travelled or turned roughly twice the expected distance (e.g., turning 180 degrees instead of 90) because the simulation accumulated two ticks (0.1s total) per logic cycle instead of one (0.05s).
  * **Fix:** `set_motors` has been restructured in standard templates. Student control loops should call `set_motors` appropriately so time advancement is tightly coupled and predictable.

---

## 7. Official Repository Structure
To prevent autograder scripts and simulation engines from leaking into student submissions, the repository is structured as follows:
* **`build/`**: **Central Build & Code-Generation Directory.** (Ignored by git). Contains:
  - CMake compilation targets, object files, and binaries.
  - Simulink code-generation folders (`UCT_KDeploy_ert_rtw/`) and simulation cache folders (`slprj/`), automatically redirected here via `startup.m` to prevent root directory clutter.
* **`python/`**: **The Python Development Area.** Shared by MicroPython and PikaScript. Contains the student entry script `main.py` (default template), mock VCP libraries (`uct_mouse.py`, `micromouse.py`), and milestone-specific student scripts (`milestone1_square.py`, `milestone2_maze.py`). The deployer (`deploy.py`) and autograder select the active target dynamically.
* **`firmware/`**: **Central compiled binaries folder.** Stores final flashable firmware binaries (`micropython.bin`, `pikascript.bin`, `simulink.bin`) so students can deploy precompiled engines without local compiler toolchains.
* **`src/`**: **Core Source Directories.** Contains:
  - `src/kernel/`: The base language-agnostic C-Kernel.
  - `src/micropython/`: Board configuration and custom firmware sources for MicroPython.
  - `src/pikascript/`: Custom firmware sources for PikaScript.
* **`matlab/`**: **MATLAB & Simulink Simulator / Models.**
  - `matlab/simulink/`: The student-facing Simulink development models (`StudentTemplate.slx`, `UCT_KDeploy.slx`), launch helper (`launch_virtual_testbed.m`), and standalone PC client code.
  - `matlab/simulator/`: Isolated physical plant engines (e.g., `dhaouadi2013_lib.slx`).
  - `matlab/attic/`: Deprecated or unused MATLAB models/tasks.
* **`autograder/`**: **The Judge.** Root-level autograding suite containing assignments configuration (`assignments/`), package builder (`build_zip.py`), execution scripts (`grade_runner.py`), and setup scripts (`setup.sh`).
* **`tools/`**: **Developer & Deployment Utilities.** Contains active support scripts (`deploy.py`, `physics_sim.py`, `steer_mouse.py`, `compile_simulink_pc.py`) and an `attic/` folder for inactive/developer-scratch files.
