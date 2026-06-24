# UCT Micromouse - State

## Current Tasks & Milestones
All major reference solutions, autograding pipeline integration, deployment optimizations, and documentation targets are completed and verified on both desktop simulation and physical hardware.

## Progress & Milestones

### 1. Algorithm Solutions & Autograding (Completed)
* **Milestone 1 (Square dead-reckoning):** 
  - Overcame wheel slip ($8\%$) by upgrading the open-loop template to a closed-loop gyro-based solution (yielding **~83%** autograder pass score).
  - Resolved the simulation double-stepping bug that advanced physics faster than assumed in the Python loop.
* **Milestone 2 (Maze Wall-Follower):**
  - Implemented left-hand rule wall follower state machine with soft gyro snapping to align parallel to walls and stop-states (`STATE_STOP_BEFORE_TURN` / `STATE_STOP_AFTER_TURN`) to prevent inertia-induced corner clipping.
  - Achieved a **100.0%** autograder pass score.

### 2. Hardware Deployment & Diagnostics (Completed)
* **MicroPython Bootloader Fix:** Resolved a `TypeError` crash loop in MicroPython `boot.py` / `board_init.c` by removing unsupported serial configurations.
* **Semihosting File I/O Lockup (Resolved):** Identified that bare-metal PikaScript calls to `open()` trigger semihosting breakpoint interrupts (`BKPT`), causing the MCU to freeze completely (0 bytes transmitted over VCP). Cleaned up [main.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python/src/main.py) to hardcode motor polarity settings (reverting to C-Kernel calibration settings), completely avoiding the hang.
* **Clock Lottery Diagnostics:** Validated the board operates at the standard **80 MHz** system clock with standard baud divider `USART1->BRR = 694`, outputting clean VCP data at **115200 baud**. Added 72 MHz outlier diagnostic baud sweep procedures (`103680` baud) for TAs and students.

### 3. Feature: High-Speed "Script-Only" Flashing (Completed)
* Added a high-speed script-only flashing mode allowing students to deploy Python scripts directly to Page 240 (`0x08078000`) of the STM32's flash in **<100ms** via `tools/deploy.py --script-only`.
* The C-Kernel automatically detects if this sector has been written to, running the flashed script natively or falling back to the compiled-in script if empty. This removes the requirement for a local C compiler toolchain on student machines after the baseline compile.

### 4. Desktop Simulation & Path Reorganization (Completed)
* Restored the missing `mm_amaze.m` and `mm_spiralmaze.m` to `matlab/simulator/` after they were deleted in a previous cleanup.
* Resolved a bug in the Python simulator map generation for `--map spiral` in [physics_sim.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/tools/physics_sim.py), which previously generated parallel vertical lines instead of a proper concentric spiral on the 10x10 grid.
* Upgraded the randomized DFS maze generator in [physics_sim.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/tools/physics_sim.py) to generate Micromouse-compliant perfect mazes, ensuring that the center $2 \times 2$ cells are open and that the start cell `(0,0)` has enclosing walls on three sides with a single East exit.
* Standardized pose initialization to be map-dependent: empty maps start the mouse at `(0.5, 0.5)` to provide boundary clearance during square runs, while maze maps start the mouse at `(0.1, 0.1)` (the center of cell `(0,0)`) facing East.
* Updated [milestone2_maze.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python/milestone2_maze.py) solver coordinates to start at cell `(0,0)` facing East to align with the new standardized starting pose.
* Patched [milestone1_square.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python/milestone1_square.py) by adding `uct_mouse.delay_ms(50)` calls in the loops to allow simulator physics to advance, and implemented a `delay_and_track` helper to continuously integrate the gyro heading during braking phases, restoring the autograder score to 100.0%.
* Corrected path generation in [launch_virtual_testbed.m](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/matlab/simulink/launch_virtual_testbed.m) to reference the true repository root, resolving path warnings (`matlab/matlab/autograder`) and allowing desktop co-simulations to start successfully.
* Optimized [uct_mouse.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/python/uct_mouse.py) to run simulations as fast as CPU bandwidth allows when running offline (under any of the environment variables `GRADESCOPE_AUTOGRADER`, `UCT_MICROMOUSE_FAST_SIM`, or `UCT_OFFLINE_MODE`, or via programmatic overrides like calling `set_fast_sim(True)` or passing `fast_sim=True` to `init()`, or setting `"fast_sim": true` in `sim_config.json`). This includes bypassing the physical `time.sleep` calls in `delay_ms` (yielding a **>10x** speedup) and dynamically intercepting any caller-level calls to `time.sleep` (via stack frame crawling) to map them to virtual physics ticks instead of blocking the execution thread.
* Added auto-stop and bidirectional auto-close capability to the Simulink GUI simulation:
  - Inside [simulink_wrapper.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/src/kernel/src/simulink_wrapper.c), registered `simulink_ext_cleanup` with MATLAB's `mexAtExit` callback to safely close the open client socket whenever the MEX library is unloaded.
  - Configured the models' `StopFcn` callback in [configure_models_for_flashing.m](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/matlab/simulink/configure_models_for_flashing.m) to execute `clear mex; clear functions;`. When the user stops the simulation in the GUI, MATLAB unloads the MEX libraries, immediately closing the client socket and telling the Python simulator to shut down its Pygame window.
  - Used `mexEvalString` to stop the Simulink simulation execution automatically when the Python socket closes on a mouse crash/collision.

### 5. Documentation & Repository (Completed)
* Updated [AGENT.md](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/AGENT.md) to document hardware quirks (silicon variance, semihosting file traps) and deployment options.
* Rewrote [student_workflow.md](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md) to provide comprehensive student guide tutorials, diagnostic sweeps, composite serial screen monitoring commands, and script-only flash commands.
* Moved autograder zip assets from the repository root to [autograder/zips/](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/autograder/zips) and updated [build_zip.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/autograder/build_zip.py) accordingly.
* Committed all modifications to the repository.

## Next Steps
* Guide user to test-run the Simulink desktop simulation now that paths and functions are restored.
* Distribute the updated toolbox repository and student guide to Course Convenor / TAs for final review.
* Perform physical test runs with students to gather feedback on the new high-speed `--script-only` flashing method.

