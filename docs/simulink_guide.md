# Simulink Development & Autograding Developer Guide

This document describes how to use MATLAB/Simulink for development on the UCT Micromouse project, detailing the model workspace configurations, PC desktop co-simulation, hardware compilation, and autograding pipeline.

---

## 1. Directory Structure & Path Initialization

To prevent compiled artifacts and cache folders from polluting the repository root, all simulation and code generation paths are dynamically redirected:

*   **`startup.m` (under `matlab/`):** Must be run when opening MATLAB. Navigate into the `matlab/` directory and run `startup.m`. It automatically sets the MATLAB search path and configures the Simulink file generation folders to output strictly to `build/slprj/` and `build/UCT_KDeploy_ert_rtw/`.
*   **Models Path:** All templates and models reside under [matlab/simulink/](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/matlab/simulink).

---

## 2. Abstraction Layer & The C-Caller Blocks

Simulink models interact with sensors and actuators using the C-Caller blocks mapping to the functions declared in `simulink_wrapper.c`:

*   `simulink_ext_set_motors(left_pwm, right_pwm)`: Sets motor duty cycles.
*   `simulink_ext_get_tof(tof_array)`: Populates a 3-element array with left, center, and right ToF distances (mm).
*   `simulink_ext_get_encoders(encoder_array)`: Populates a 2-element array with left and right wheel encoder counts.
*   `simulink_ext_get_vbatt()`: Returns battery voltage.
*   `simulink_ext_get_gyro()`: Returns the gyroscope Z-axis angular velocity.

Depending on where the code is executing, the wrapper behaves polymorphically:
1.  **On PC (Simulation/Autograder):** Emits JSON telemetry frames over a TCP/IP loopback socket on `localhost:8000` to a background physics simulator.
2.  **On Hardware (STM32):** Interacts directly with the C-Kernel registers, bypassing the network socket code.

---

## 3. Co-Simulation & Interactive Testing

Students can co-simulate their Simulink algorithms against the virtual testbed environment automatically with full GUI integration:

1.  **Open the Top-Level Model:** Open `UCT_KDeploy.slx` in Simulink.
2.  **Access the Controller:** Locate the referenced `StudentTemplate` Model Reference block inside it. Double-click it to open, view, and edit your controller logic (which edits the underlying `StudentTemplate.slx` file). If you are working on a specific milestone, you can also change the model file pointed to by this Model Reference block (e.g. to `milestone1_square.slx`).
3.  **Run Simulation:** Click **Run** on either `UCT_KDeploy.slx` or `StudentTemplate.slx`.
4.  **Automatic Launch:** The model's `StartFcn` callback will automatically launch the Python-based virtual maze engine (`physics_sim.py`) in the background. The Pygame visual simulator window will appear automatically.
5.  **Automatic Stop & Cleanup:** 
    - Clicking **Stop** in the Simulink GUI will automatically close the Pygame window and stop the simulation.
    - If the virtual mouse crashes or you manually close the Pygame window, the background socket disconnection will immediately trigger Simulink to stop running the model.

---

## 4. Calibrating Motor and Encoder Polarities

Because physical wiring and motor soldering directions vary across robot chassis, students must ensure motor actuation and encoder tracking values are mathematically aligned (e.g., forward PWM drives the mouse forward, and forward travel yields positive encoder counts).

In Simulink, this polarity correction is handled graphically in your model:
1.  **Motor Polarity:** If a motor rotates backwards under positive command, place a **Gain block** (set to `-1`) on that motor's command line immediately before passing the signal to the `simulink_ext_set_motors` block.
2.  **Encoder Polarity:** If an encoder counts down when the wheel rotates forward, place a **Gain block** (set to `-1`) on that encoder's feedback line immediately after the output of the `simulink_ext_get_encoders` block.

This visual mapping isolates your algorithm from physical chassis differences and ensures perfect parity when your model is compiled and executed in the autograder (where the virtual environment assumes standard positive polarities).

---

## 5. Hardware Compilation (`Cmd+B`)

When ready to deploy to the physical mouse:
1.  Open `UCT_KDeploy.slx`.
2.  Press **Cmd+B** (or Ctrl+B on Windows/Linux) to trigger the Embedded Coder build pipeline.
3.  Simulink will generate optimized ANSI C code and output it to the `firmware/build/UCT_KDeploy_ert_rtw/` directory.
4.  The `CMakeLists.txt` inside the `firmware/` folder automatically compiles this generated source code into the final STM32 flashable firmware target.

---

## 6. Autograding Submission & PC Build Compilation

When a student submits their Simulink project for grading, the hosted Gradescope autograder:
1.  Detects the presence of the code-generation directory under `firmware/build/UCT_KDeploy_ert_rtw/`.
2.  Invokes `tools/compile_simulink_pc.py` to compile the generated C code into a native desktop executable, linking the testbed mock client harness `PC_client_main.c` and `simulink_wrapper.c`.
3.  Launches this compiled executable in a lock-step loopback connection to evaluate the milestone parameters (e.g., executing a square or navigating a maze).
4.  Scores and exports grading logs to Gradescope.
