# UCT-Micromouse: Visual Simulation & STM32 Hardware Control Testbed

Welcome to the visual desktop simulation testbed and hardware compilation framework for the autonomous **UCT Micromouse** robots.

This project supports dual-path programming using **Python (MicroPython)** or **MATLAB/Simulink**.

> [!IMPORTANT]
> **No physical hardware is required to run the desktop physics simulator and test your algorithms!**

---

## 🚀 Choose Your Path to Get Started

Select the guide below matching your role and development toolchain:

### 🐍 [Track A: Python (MicroPython) Quickstart](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/getting_started_python.md)
*For students writing algorithms in Python. Learn how to flash the interpreter, write to the USB drive, open the REPL, and write your first motor-spinning script.*

### 📐 [Track B: Simulink Quickstart](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/getting_started_simulink.md)
*For students building block-based control algorithms in Simulink. Learn how to initialize your workspace, run the Pygame desktop simulator, and cross-compile/flash your model to the microcontroller.*

### 👩‍🏫 [Track C: Staff & TA Reference Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/getting_started_staff.md)
*For convenors, tutors, and TAs managing the lab. Learn how to run automated board factory resets, inspect raw flash hardware, and execute Gradescope autograder test suites locally.*

---

## ⚠️ Critical Hardware Safety Warnings (Prevent Damage to Your Mouse)

To prevent permanent damage, component failure, or destroying your Micromouse hardware, you must strictly follow these three safety rules:

*   **Avoid Multiple USB Connections (Ground Loop Prevention)**: 
    To protect your hardware (microcontroller, power board, and laptop/charger) from ground loop damage, **never plug in more than one USB cable at a time.** Do not simultaneously connect USB cables to the power board, the processor board, and the ST-Link debugger. Always use a single cable connected exclusively to the ST-Link debugger port.
*   **Do Not Connect Battery While USB is Attached**: 
    Never plug the battery into the main power board while any USB cables are connected to the mouse. Doing so can cause power contention and catastrophic failure (e.g. burn out) of the onboard boost converter.
*   **Do Not Rotate Wheels Manually/Externally**: 
    The wheels are connected to a high-ratio gearbox that is not back-drivable. Forcing the wheels to spin by hand back-drives the gearbox, which is highly likely to strip the gears and permanently destroy the motor assembly.

---

## 📂 Repository Sitemap & Resources

If you need deeper reference documents, explore these guides:
*   **[Course Handbook](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/EEE3097_8_9S_Course_Handbook_2026.md):** The primary master document containing milestone descriptions, grading criteria, and ECSA compliance rubrics.
*   **[Hardware Setup & Calibration Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/hardware_setup.md):** Peripheral details and motor polarity calibration.
*   **[Kernel & API Developer Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/kernel_api_guide.md):** Reference documentation detailing the underlying C-Kernel telemetry structure and Python API.
*   **[Simulink Development & Autograding Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/simulink_guide.md):** Details on code generation settings and compiler paths.
