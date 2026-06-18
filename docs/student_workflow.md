# Student Workflow Guide

Welcome to the UCT Micromouse project! This guide will walk you through how to develop your algorithms, test them in simulation, and deploy them to the physical hardware.

## 1. Development Options

The project is designed with a polymorphic software layer, meaning the exact same algorithm code can run in a virtual desktop environment and on the actual STM32 physical mouse without modification. You have two main avenues for development:

### Option A: Python (MicroPython / PikaScript)
You can write your algorithms entirely in Python.
1. Start with the `python/main.py` script or the specific milestone templates (e.g., `python/milestone1_square.py`).
2. Use the `uct_mouse` library functions to command the robot (e.g., `mouse.set_motors(left, right)`, `mouse.get_tof_l()`).
3. For Python development, your code is executed through a proxy when testing on the desktop autograder.

### Option B: MATLAB / Simulink
You can build block-based visual algorithms in Simulink or C-Caller architectures.
1. Use the `matlab/simulink/StudentTemplate.slx` as your base workspace.
2. Build your control logic using standard Simulink blocks and our provided subsystem abstractions.
3. Use the Simulink Coder to generate C-code that directly hooks into the Tier-1 Micromouse C-Kernel.

## 2. Testing in Co-Simulation (Desktop)

Before risking physical hardware, verify your algorithm in the virtual maze.

### For Python:
- Run your script against the autograder or the `physics_sim.py` testing engine.
- Example: `python tools/physics_sim.py` (which launches the virtual testbed on `localhost:8000`).
- Run your script (e.g., `python python/milestone1_square.py`). The script will automatically connect to the local socket and actuate the virtual mouse.

### For Simulink:
- Open `StudentTemplate.slx` and click **Run**.
- The model will compile the desktop wrapper and connect to the built-in physics engine.
- You can visualize the mouse's path directly in MATLAB scopes or the virtual 3D viewer.

## 3. Deploying to the Physical Mouse

Once your code works perfectly in simulation, it's time to flash it to the physical mouse.

### Physical Setup
1. Turn on the mouse using the physical battery switch.
2. Connect the mouse to your laptop via USB-C.
3. Ensure the serial COM port is recognized (e.g., `/dev/cu.usbmodem*` on Mac/Linux, `COM*` on Windows).

### Flashing Python Code
1. We use a firmware base that hosts the Python engine. Ensure the correct binary (`firmware/pikascript.bin` or `firmware/micropython.bin`) is flashed onto your STM32 Nucleo board using STM32CubeProgrammer or simple USB Mass Storage drag-and-drop (if applicable).
2. Use the deployment utility to push your python file:
   ```bash
   python tools/deploy.py --file python/milestone1_square.py
   ```
3. The mouse will reboot and immediately begin executing your code.

### Flashing Simulink / C Code
1. In your `StudentTemplate.slx` model, click **Build** or hit `Cmd+B` (`Ctrl+B`).
2. Simulink Embedded Coder will generate the C equivalents of your block model.
3. The automated deployment hook will compile the Tier-1 kernel together with your logic and flash the `simulink.bin` directly to the STM32 over USB.
4. The physical mouse will run the hardware control loop identically to your desktop simulation.

## 4. Hardware Quirks & Debugging

- **Silicon Variants:** Some STM32 processors run at `72 MHz` while others are `80 MHz`. If you experience serial terminal hanging or gibberish text, let a TA know so your board's PLL divider can be updated.
- **Timing and Loops:** When using Python, try to group your `set_motors()` calls to occur once per logical control loop. Placing multiple blocking calls or combining `set_motors()` and `delay_ms()` improperly can cause timing mismatches between simulation time steps and physical time.
- **Motor Polarity:** If the mouse drives in reverse, verify that your software variables aren't flipped before assuming a hardware flaw.
