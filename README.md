# UCT-Micromouse: Visual Simulation & STM32 Hardware Control Testbed

[![Open in MATLAB Online](https://www.mathworks.com/images/responsive/global/open-in-matlab-online.svg)](https://matlab.mathworks.com/open/github/v1?repo=nicollsf/UCT-Micromouse)

This repository provides a complete, visual desktop simulation testbed and hardware compilation framework for autonomous **Micromouse** robots. Developed at the University of Cape Town (UCT), it supports dual-path programming using **MATLAB/Simulink/Stateflow** or **Python** (MicroPython/PikaScript).

**No physical hardware is required to run the desktop physics simulator and test your algorithms!**

---

## 🚀 Quickstart: Run the Visual Simulator (No Hardware Needed)

You can run your control algorithms in interactive desktop co-simulation in under a minute:

1. **Initialize the Workspace**: Open MATLAB in the project root directory and run `startup.m`. This adds the required folders to the MATLAB search path and configures cache/build directories.
2. **Open the Model**: Navigate to `matlab/simulink/` and open `StudentTemplate.slx`.
3. **Run the Simulation**: Click the **Run** button in the Simulink toolbar. The 2D Pygame-based maze physics simulator will launch automatically in a background task, showing your virtual mouse traversing the maze.
4. **Iterate**: Modifying your controller in Simulink updates the mouse behavior dynamically in the visual simulator window. Clicking **Stop** in Simulink automatically closes the visualization window.

---

## 🛠️ Hardware Deployment Target
When deploying to a physical differential-drive mouse:
* The codebase targets an **STM32 Nucleo** microcontroller board routing quadrature wheel encoders, a 3-axis IMU gyroscope, three Time-of-Flight (ToF) distance sensors, downward-facing line sensors, and an SSD1306 OLED display.
* **Polymorphic Architecture**: The C-Caller block architecture executes loopback socket communication on the desktop but compiles directly to bare-metal hardware registers when built with the Embedded Coder (`Cmd+B` / `Ctrl+B` in `UCT_KDeploy.slx`), ensuring the exact same controller code runs in both virtual and physical worlds.

---

## 📦 Note on Cloning & File Exchange ZIP Downloads
* **If you cloned via Git**: This repository utilizes submodules for the bare-metal microcontroller kernel. Ensure you clone recursively:
  ```bash
  git clone --recursive https://github.com/nicollsf/UCT-Micromouse.git
  ```
  If already cloned without submodules, initialize them using:
  ```bash
  git submodule update --init --recursive
  ```
* **If you downloaded the `.zip` from MATLAB File Exchange**: The `external/` submodule directories will be empty by default. **This does not affect the desktop simulation.** You can still run the visual co-simulation in MATLAB out of the box. The submodules are only required if you intend to cross-compile the code into STM32 binary firmware.

---

## 📚 Master Documentation Index

All `.md` (Markdown) files in this repository are the **definitive master sources** of truth for this course. PDF files provided on D2L (Amathuba) are generated directly from these documents. 

### How to Read Markdown Files
*   **In VS Code:** Open any `.md` file and press **`Ctrl+Shift+V`** (or **`Cmd+Shift+V`** on macOS) to open the rich styled preview.
*   **In a Browser:** Install the *Markdown Viewer* extension for Chrome/Firefox to open local `.md` files directly in your browser.

A complete, detailed index of all project guides is located in the **[Documentation Index (docs/README.md)](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/README.md)**. Key quick links include:
*   [Primary Student Handbook](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/EEE3097_8_9S_Course_Handbook_2026.md) ([PDF version](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/EEE3097_8_9S_Course_Handbook_2026.pdf)): The master guidelines, ECSA compliance criteria, and graded milestone rubrics.
*   [Milestone 0: Hardware Verification Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assignments/submission0_milestone0_verification.md): Physical assembly, verification checks, and telemetry setup.
*   [Project Workflow & Setup](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md): Setup environment, simulation execution, and VCP code flashing.

---

## ⚠️ Critical Hardware Safety Warnings (Prevent Damage to Your Mouse)

To prevent permanent damage, component failure, or destroying your Micromouse hardware, you must strictly follow these three safety rules:

*   **Avoid Multiple USB Connections (Ground Loop Prevention)**: 
    To protect your hardware (microcontroller, power board, and laptop/charger) from ground loop damage, **never plug in more than one USB cable at a time.** Do not simultaneously connect USB cables to the power board, the processor board, and the ST-Link debugger. Always use a single cable connected exclusively to the ST-Link debugger port.
*   **Do Not Connect Battery While USB is Attached**: 
    Never plug the battery into the main power board while any USB cables are connected to the mouse. Doing so can cause power contention and catastrophic failure (e.g. burn out) of the onboard boost converter.
*   **Do Not Rotate Wheels Manually/Externally**: 
    The wheels are connected to a high-ratio gearbox that is not back-drivable. Forcing the wheels to spin by hand back-drives the gearbox, which is highly likely to strip the gears and permanently destroy the motor assembly.


