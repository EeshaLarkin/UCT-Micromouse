# Simulink Development & Autograding Developer Guide

This document describes how to use MATLAB/Simulink for development on the UCT Micromouse project, detailing the model workspace configurations, PC desktop co-simulation, hardware compilation, and autograding pipeline.

---

## 1. Directory Structure & Path Initialization

To prevent compiled artifacts and cache folders from polluting the repository root, all simulation and code generation paths are dynamically redirected:

*   **`startup.m` (Root-Level):** Must be run when opening MATLAB in the project root. It automatically sets the MATLAB search path and configures the Simulink file generation folders to output strictly to `build/slprj/` and `build/UCT_KDeploy_ert_rtw/`.
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

1.  **Run Simulink Model:** Open `StudentTemplate.slx` and click **Run**.
2.  **Automatic Launch:** The model's `StartFcn` callback will automatically launch the Python-based virtual maze engine (`physics_sim.py`) in the background. The Pygame visual simulator window will appear automatically.
3.  **Automatic Stop & Cleanup:** 
    - Clicking **Stop** in the Simulink GUI will automatically close the Pygame window and stop the simulation.
    - If the virtual mouse crashes or you manually close the Pygame window, the background socket disconnection will immediately trigger Simulink to stop running the model.

---

## 4. Hardware Compilation (`Cmd+B`)

When ready to deploy to the physical mouse:
1.  Open `UCT_KDeploy.slx`.
2.  Press **Cmd+B** (or Ctrl+B on Windows/Linux) to trigger the Embedded Coder build pipeline.
3.  Simulink will generate optimized ANSI C code and output it to the `build/UCT_KDeploy_ert_rtw/` directory.
4.  The top-level `CMakeLists.txt` automatically compiles this generated source code into the final STM32 flashable firmware target.

---

## 5. Autograding Submission & PC Build Compilation

When a student submits their Simulink project for grading, the hosted Gradescope autograder:
1.  Detects the presence of the code-generation directory under `build/UCT_KDeploy_ert_rtw/`.
2.  Invokes `tools/compile_simulink_pc.py` to compile the generated C code into a native desktop executable, linking the testbed mock client harness `PC_client_main.c` and `simulink_wrapper.c`.
3.  Launches this compiled executable in a lock-step loopback connection to evaluate the milestone parameters (e.g., executing a square or navigating a maze).
4.  Scores and exports grading logs to Gradescope.
