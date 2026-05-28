# AI_CONTEXT.md

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
3. **Phase 3 (Upcoming):** Verify Simulink autograder TCP/IP integration and evaluate Tier 3 userland maze-solving scripts.
4. **Phase 4 (Upcoming):** Implement the hardware timer interrupts (EXTI/TIM) for the wheel encoders in the C-Kernel to close the physical control loop.

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

## 7. Official Repository Structure
To prevent autograder scripts and simulation engines from leaking into student submissions, the MATLAB repository is strictly divided:
* **`matlab/models/`**: **The Brain.** Contains strictly student-facing deployment models (`StudentTemplate.slx`, `UCT_KDeploy.slx`) and student utility block libraries (`devel_lib.slx`).
* **`matlab/simulator/`**: **The Body.** Contains the isolated physical plant engines (`dhaouadi2013_lib.slx`). 
* **`matlab/autograder/`**: **The Judge.** Contains the unified TCP server, maze matrices, and milestone evaluation scripts.

---

## 6. Hardware Quirks & Known States
* **The 72 MHz / 80 MHz Silicon Lottery:** Due to grey-market silicon or missing HSI factory calibration trims in this specific batch of STM32s, some boards successfully achieve the targeted `80 MHz` PLL clock, while identically flashed sister boards cap out at `72 MHz`.
  * **Impact:** A board running at 72 MHz while programmed for 80 MHz will calculate incorrect UART baud dividers (an 11.1% error), causing the Python dashboard to see garbage hex and hang on connection.
  * **Fix:** The standard firmware strictly targets the healthy `80 MHz` (using `USART1->BRR = 694`). If a specific chassis hangs on connect but runs perfectly when the divider is swapped to `625`, that board is a 72 MHz outlier and must be labelled.
* **Randomized Motor Polarity:** Depending on how the physical DC motor leads were soldered by students/technicians, the chassis might spin backwards or in circles when given a forward command.
  * **Impact:** If students try to flip negative signs in their high-level PID math, their code will fail against the standardized Simulink Autograder.
  * **Fix:** Abstracted at the Tier 1 level. The C Kernel uses `#define POLARITY_L` and `POLARITY_R` (set to `1` or `-1`) in `micromouse_kernel.c` to mathematically normalize the physical wiring before the PWM pulse ever hits the timer register.
* **Left Motor Reverse Casting Bug:** In older ARM GCC toolchains, passing a signed 8-bit negative integer into the standard `<stdlib.h>` `abs()` function mangles the sign bit, causing the left wheel to brake instead of reverse. The C Kernel explicitly bypasses this with a native hardware timer override (`TIM3->CCR4 = -actual_l`).