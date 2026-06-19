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
* Developed a script-only flashing mode allowing students to deploy Python scripts directly to Page 240 (`0x08078000`) of the STM32's flash in **<100ms** via `tools/deploy.py --script-only`.
* The C-Kernel automatically detects if this sector has been written to, running the flashed script natively or falling back to the compiled-in script if empty. This removes the requirement for a local C compiler toolchain on student machines after the baseline compile.

### 4. Documentation & Repository (Completed)
* Updated [AGENT.md](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/AGENT.md) to document hardware quirks (silicon variance, semihosting file traps) and deployment options.
* Rewrote [student_workflow.md](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md) to provide comprehensive student guide tutorials, diagnostic sweeps, composite serial screen monitoring commands, and script-only flash commands.
* Moved autograder zip assets from the repository root to [autograder/zips/](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/autograder/zips) and updated [build_zip.py](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/autograder/build_zip.py) accordingly.
* Committed all modifications to the repository.

## Next Steps
* Distribute the updated toolbox repository and student guide to Course Convenor / TAs for final review.
* Perform physical test runs with students to gather feedback on the new high-speed `--script-only` flashing method.
