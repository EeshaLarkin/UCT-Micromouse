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

#### High-Speed Offline Testing (Fast Simulation Mode)
For tasks requiring massive numbers of runs (e.g. batch testing or training reinforcement learning agents), you can bypass standard wall-clock sleep delays and run the simulation at maximum CPU speed. Fast Simulation Mode automatically intercepts and replaces ordinary `time.sleep` calls with simulator physics steps.

You can configure Fast Simulation Mode using any of the following mechanisms (evaluated in priority order):
1. **Direct Function Override:**
   ```python
   import uct_mouse
   uct_mouse.set_fast_sim(True)  # Dynamically enables high-speed simulation & intercepts time.sleep
   ```
2. **Initialization Argument:**
   ```python
   import uct_mouse
   uct_mouse.init(fast_sim=True)  # Forces fast simulation when establishing simulation connection
   ```
3. **JSON Settings (`sim_config.json`):**
   Add the `"fast_sim": true` parameter to `python/sim_config.json`:
   ```json
   {
     "backend": "python",
     "auto_start": true,
     "fast_sim": true
   }
   ```
4. **Environment Variables:**
   Set one of the environment variables in your terminal shell:
   * `UCT_MICROMOUSE_FAST_SIM=1`
   * `UCT_OFFLINE_MODE=1`

### For Simulink:
- Open `StudentTemplate.slx` and click **Run**.
- The model will automatically launch the Pygame virtual physics simulator window in the background and connect to it.
- Letting the mouse crash or manually closing the Pygame window will automatically stop the Simulink simulation.
- Clicking **Stop** in the Simulink GUI will automatically stop the simulation and close the Pygame window.
- You can visualize the mouse's path directly in the Pygame window or standard MATLAB scopes.

## 3. Deploying to the Physical Mouse

Once your code works perfectly in simulation, it's time to flash it to the physical mouse.

### Physical Setup
1. Turn on the mouse using the physical battery switch.
2. Connect the mouse to your laptop via USB-C.
3. Ensure the serial COM port is recognized (e.g., `/dev/cu.usbmodem*` on Mac/Linux, `COM*` on Windows).

### Flashing Python Code
1. We use a firmware base that hosts the Python engine. Ensure the correct binary (`firmware/binaries/pikascript.bin` or `firmware/binaries/micropython.bin`) is flashed onto your STM32 Nucleo board using STM32CubeProgrammer, USB Mass Storage drag-and-drop, or `st-flash`.
2. For **MicroPython**, deploy using the serial virtual com port utility:
   ```bash
   python tools/deploy.py --engine micropython --script python/milestone1_square.py
   ```
3. For **PikaScript**, you can choose between two methods:
   * **Full Compile & Flash (Requires a local C compiler toolchain):**
     ```bash
     python tools/deploy.py --engine pikascript --script python/milestone1_square.py
     ```
   * **High-Speed Script-Only Flash (Requires `st-flash` utility; runs in <100ms and does NOT require a local C compiler toolchain):**
     ```bash
     python tools/deploy.py --engine pikascript --script python/milestone1_square.py --script-only
     ```
4. The mouse will reboot and immediately begin executing your code.

### Flashing Simulink / C Code
1. In your `StudentTemplate.slx` model, click **Build** or hit `Cmd+B` (`Ctrl+B`).
2. Simulink Embedded Coder will generate the C equivalents of your block model.
3. The automated deployment hook will compile the Tier-1 kernel together with your logic and flash the `simulink.bin` directly to the STM32 over USB.
4. The physical mouse will run the hardware control loop identically to your desktop simulation.

## 4. Hardware Quirks & Debugging

- **Silicon Clock Variants (72 MHz vs 80 MHz):** Due to manufacturing variance, some boards run their system clock at 72 MHz instead of the targeted 80 MHz. 
  - **Symptoms:** Gibberish text or terminal hanging when communicating at 115200 baud.
  - **Diagnosis (Baud Sweep):** Try connecting to the serial port `/dev/cu.usbmodem*` (or COM port) at `103680` baud ($115200 \times \frac{72}{80}$). If you see clean telemetry text at this speed, your board is running at 72 MHz.
  - **Fix:** Notify a convener/TA to label your board, and change the UART baud rate divider in `firmware/src/main.c` from `694` to `625` before building.
- **The Semihosting File I/O Lockup:** PikaScript runs bare-metal without an operating system or file system.
  - **Warning:** Executing file operations in Python (like `open()`, `with open(...)`, etc.) calls C standard library filesystem hooks. These hooks trigger **Semihosting** by issuing an ARM breakpoint instruction (`BKPT 0xAB`), which halts the MCU immediately if no active debugger is listening. The serial interface will go completely silent (0 bytes transmitted).
  - **Rule:** Never use `open()` or file operations in Python scripts compiled for PikaScript deployment. All configuration constants (like polarity multipliers) must be hardcoded in Python code.
- **Timing and Loops:** When using Python, try to group your `set_motors()` calls to occur once per logical control loop. Placing multiple blocking calls or combining `set_motors()` and `delay_ms()` improperly can cause timing mismatches between simulation time steps and physical time.
- **Motor Polarity:** If the mouse drives in reverse, verify that your software variables aren't flipped before assuming a hardware flaw.

### Debugging & Telemetry over ST-Link VCP
When running the PikaScript or Simulink firmware on the silicon, the board uses its Virtual COM Port (VCP) over the USB cable for print statements and telemetry data.
1. **Telemetry Stream:** By default, the board streams sensor telemetry (ToF values, Gyro, Battery voltage) as JSON-lite text frames (e.g. `{"tof_c":706,"gyro":0.004,"v_batt":4.07}`) at 115200 baud.
2. **Standard Output (stdout):** Any Python `print(...)` statements are multiplexed directly into this stream.
3. **Serial Terminal Monitor:** You can monitor the raw output using any serial terminal tool (e.g. Serial, PuTTY, or a simple python script) set to 115200 baud. For example, to read output from macOS terminal:
   ```bash
   screen /dev/cu.usbmodem* 115200
   ```
   *(Press `Ctrl+A` then `Ctrl+\` and confirm `y` to exit the screen command.)*

### MicroPython REPL Debugging
If you are using the **MicroPython** engine instead of PikaScript, you can debug runtime crashes dynamically using the REPL:
1. Make sure no other terminal or software is locking the serial port `/dev/cu.usbmodem*` (or `COM*`).
2. Connect to the board's serial console:
   ```bash
   python -m mpremote repl
   ```
3. Once connected, press **Ctrl+D** to trigger a soft-reboot. 
4. The terminal will display the full Python error traceback showing the exact file name and line number causing the crash.
5. Press **Ctrl+]** (or **Ctrl+x**) to exit the REPL shell.
* **Tip (Interactive Execution):** You can also use the REPL as an interactive shell. At the `>>>` prompt, you can type Python code directly (e.g., `import uct_mouse` followed by `uct_mouse.get_tof()` or `uct_mouse.set_motors(30, 30)`) to query sensors or actuate motors in real time.

