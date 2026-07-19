# AGENT.md

## Executive Summary
This document outlines the architecture of the UCT Micromouse project, a platform for teaching embedded systems and robotics. The project is built on a three-tier architecture: a low-level C kernel for hardware control, a mid-level abstraction layer, and a high-level user application for maze-solving logic. A key feature is its polymorphic design, allowing the same student code (Python or Simulink) to run on both the physical robot and in a Simulink-based simulator for autograding. Communication between layers is handled by a lightweight JSON-based protocol. This structure provides a clear separation of concerns, enabling students to focus on algorithm development while using a robust and flexible hardware and simulation environment.

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
* **MicroPython I2C Pin/Clock Override:** During standard MicroPython VM initialization, the interpreter reconfigures and resets peripheral registers, which can disable the I2C2 clocks or revert the alternate function mode of pins `PB10`/`PB11` (used for the SSD1306 OLED display).
  * **Impact:** If `initMicroMouse()` is called from user Python land, the background I2C2 peripheral is in a disabled or unconfigured state, causing `SSD1306_Init()` to fail and keeping the OLED display completely blank.
  * **Fix:** Expose and call `MX_I2C1_Init()` and `MX_I2C2_Init()` at the very beginning of `initMicroMouse()` in `MicroMouse_main.c`. This forces the STM32 HAL library to freshly re-assert the correct I2C peripheral clocks, GPIO alternate function pins, and analog/digital filters immediately before initializing the OLED screen and VL53L0X TOF sensors.
* **OLED I2C Address Batch Discrepancy:** Different production batches of generic SSD1306 128x64/128x32 OLED screens feature physical jumper resistors on the back which select an 8-bit write address of either `0x78` or `0x7A`.
  * **Impact:** Standard firmware hardcoded to `0x78` fails to initialize and remains completely blank on chassis carrying screens soldered for `0x7A`.
  * **Fix:** Upgraded `SSD1306_Init()` in `SSD1306.c` to perform dynamic address scanning. It first queries `0x78` and falls back to `0x7A` via `HAL_I2C_IsDeviceReady()`, assigning the responding address to a dynamic `ssd1306_detected_addr` variable which replaces the preprocessor macro.
* **Randomized Motor Polarity:** Depending on how the physical DC motor leads were soldered by students/technicians, the chassis might spin backwards or in circles when given a forward command.
  * **Impact:** If students try to flip negative signs in their high-level PID math, their code will fail against the standardized Simulink Autograder.
  * **Fix:** Abstracted at the Tier 1 level. The C Kernel uses `#define POLARITY_L` and `POLARITY_R` (set to `1` or `-1`) in `micromouse_kernel.c` to mathematically normalize the physical wiring before the PWM pulse ever hits the timer register.
* **Left Motor Reverse Casting Bug:** In older ARM GCC toolchains, passing a signed 8-bit negative integer into the standard `<stdlib.h>` `abs()` function mangles the sign bit, causing the left wheel to brake instead of reverse. The C Kernel explicitly bypasses this with a native hardware timer override (`TIM3->CCR4 = -actual_l`).
* **Simulation Double-Stepping Bug (Resolved):** In earlier iterations, calling both `uct_mouse.set_motors()` and `uct_mouse.delay_ms()` within the same loop advanced the physics simulator time step twice per loop.
  * **Impact:** The mouse travelled or turned roughly twice the expected distance (e.g., turning 180 degrees instead of 90) because the simulation accumulated two ticks (0.1s total) per logic cycle instead of one (0.05s).
  * **Fix:** `set_motors` has been restructured in standard templates. Student control loops should call `set_motors` appropriately so time advancement is tightly coupled and predictable.
* **Fast Simulation Mode Configuration Interface:** To support reinforcement learning (RL) or rapid offline batch testing, the simulator can run in high-speed offline mode where standard wall-clock delays are bypassed. The state `_is_fast_sim_active` in `uct_mouse.py` is resolved dynamically in this order:
  * **Programmatic Code Override:** Call `uct_mouse.set_fast_sim(True/False)` or initialize via `uct_mouse.init(fast_sim=True/False)`.
  * **Configuration File:** Add `"fast_sim": true` or `"fast_sim": false` in `sim_config.json`.
  * **Environment Variables:** Set `GRADESCOPE_AUTOGRADER=1`, `UCT_MICROMOUSE_FAST_SIM=1`, or `UCT_OFFLINE_MODE=1`.
  * When enabled, `time.sleep` calls are dynamically intercepted via frame-stack analysis (`sys._getframe()`) and redirected to virtual simulator steps.
* **MicroPython Read-During-Write Flash Corruption (Factory Reset):** When the MicroPython internal FAT filesystem is formatted on first boot, `factory_reset_make_files` writes default files (`boot.py`, `main.py`, `README.txt`) to Flash.
  * **Impact:** Writing these files by reading directly from C string literals (which also reside in Flash) violates the STM32 single-bank Flash read-during-write hardware constraint. The AHB bus returns corrupted binary garbage, leading to a parser crash: `RuntimeError: name too long`.
  * **Fix:** Buffer default file strings into a temporary stack RAM array (`ram_buf`) before calling `f_write()`. Reading from RAM during Flash programming cycles prevents bank access collisions.
* **Unused NVIC Timer Interrupt Storms (Floating Pins):** When the mainboard is handled out-of-chassis, physical contact with the exposed pin headers (`T4C1`, `T4C2`, etc.) injects transient electrical/capacitive noise.
  * **Impact:** CubeMX enables `TIM4_IRQn` (as well as `TIM5_IRQn` and `TIM7_IRQn`) in the NVIC at Priority 0 by default. High-frequency touch noise on these floating pins registers as capture edges, triggering an interrupt storm. At Priority 0, this starves MicroPython's lower-priority SysTick timer and VM loop, causing a silent CPU freeze.
  * **Fix:** Comment out `HAL_NVIC_EnableIRQ()` for unused interrupts (`TIM4_IRQn`, `TIM5_IRQn`, `TIM7_IRQn`) inside `MX_NVIC_Init()` in both `main.c` and `MicroMouse_main.c` to prevent noise propagation to the CPU cores.
* **MicroPython I2C Bus Glitch Recovery Crash:** Physical vibration/bumps can cause transient voltage fluctuations on the I2C lines, triggering standard HAL transaction errors.
  * **Impact:** If `restartI2C()` performs a full hardware reset (`HAL_I2C_DeInit()` / `HAL_I2C_Init()`) mid-flight, it corrupts the peripheral state register expectations of the active MicroPython VM, locking up the CPU.
  * **Fix:** Recover safely in software by resetting the state handle to `HAL_I2C_StateTypeDef` `READY` and clearing `ErrorCode` to `HAL_I2C_ERROR_NONE`, without resetting the physical peripheral configuration.
* **Onboard LED Pin Mapping & Master Gating Control:** 
  * LED0 is connected to `PC13`, LED1 is connected to `PC14`, and LED2 is connected to `PC15`.
  * **Critical Gating Pin:** All three LEDs are electrically controlled/gated by pin `PB3` (`CTRL_LEDS`). `PB3` must be written `HIGH` (`GPIO_PIN_SET`) during board initialization, otherwise all LEDs will remain physically turned off regardless of the PC13/PC14/PC15 pin states.
* **External Flash Partitioning & FAT Filesystem Offset:** To avoid wearing out the internal microcontroller flash, the FAT filesystem (`UCT_MMOUSE` drive) is shifted to the last **128 KB** of the external SPI flash (logical blocks mapped with offset `0xE0000` to `0xFFFFF`).
* **JSON Telemetry Logger & Sparse Compression:** The C-Kernel automatically logs runs at **25 Hz** in a sparse JSON text format. Logging triggers automatically on first motor actuation, overwrites the previous run (resets pointer to `0x00000`), and writes to the first **896 KB** partition.
* **Unique UID & Code Verification Hashing (Anti-Cheat):** The first line of every log contains a `log_header` containing the microcontroller's unique 96-bit Device UID and a 32-bit FNV-1a checksum hash of the running Python bytecode / FAT filesystem state to verify student submission authenticity. UIDs are not registered in advance; instead, convenors check logs retrospectively for duplicate UIDs to detect shared code or drives.
* **VCP Log Dumping protocol:** Exposes serial command `{"c":{"dump":1}}` (and Python helper `uct_mouse.dump_logs()`) which pauses interrupts and dumps log bytes of the last run to the console.
* **Research Utilization of Telemetry Dataset:** The generated logs from 150+ students are aggregate-audited to build a high-fidelity system identification model of the physical mouse dynamics, and to evaluate off-board path reconstruction (e.g. Extended Kalman Filter/Smoother predictors) in robotics research.
* **Document Output Compilation Rule:** Do NOT automatically compile or generate PDF/HTML versions of planning, instructions, or course description Markdown documents in the workspace. Any document compilation must be left for the convenor to execute manually when required.
* **Primary Student Document Policy:** The course handbook `docs/EEE3097_8_9S_M0_Handbook_2026.md` is the **single, master document** disseminated to students. All project tasks, educational objectives, track streams, submission guidelines, and detailed passing/grading criteria must be maintained directly within it.
* **Markdown List Formatting Rule:** Always place a blank line (empty newline) immediately before initiating a bulleted (`*`, `-`) or numbered (`1.`) list in Markdown documents. Failing to do so causes Pandoc and other parsers to collapse the list items into inline text, rendering raw asterisks in the compiled output.
* **LMS/D2L Deploy Sync Rule:** Assume that everything in the `workspace/deploy/` folder has been provided to students on D2L. If any changes are made to reference documents (under `docs/` or `docs/assignments/`), you must notify the convenor that they must rebuild and push the updated PDFs to D2L (Amathuba) to prevent synchronization drift.





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
