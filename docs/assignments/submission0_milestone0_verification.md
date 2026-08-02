# **Milestone 0: Hardware Verification & Telemetry Guide**

This guide outlines the step-by-step verification process ("Milestone 0") to confirm that your assembled and soldered Micromouse hardware is fully functional before you begin writing maze-solving algorithms. 

To ensure absolute reliability, this verification process uses the **PikaScript (C-Kernel)** base firmware and the interactive **Keyboard steering Dashboard**.

---

## **1. Construction Resources & Assembly Guides**

Before you begin assembling and soldering your Micromouse chassis, consult the reference documents and media located in the [docs/assembly/](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assembly) folder:

*   **Step-by-Step Assembly Guide (PDF):** [micro-mouse_assembly.pdf](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assembly/micro-mouse_assembly.pdf) — Contains detailed diagrams and soldering instructions.
*   **Comprehensive Construction Video:** [mmassembly.mp4](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assembly/mmassembly.mp4) — A visual walkthrough showing soldering, chassis assembly, and component installation.
*   **Electrical Schematics (PDF):** [mm_schematics.pdf](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assembly/mm_schematics.pdf) — Schematic diagrams of the main power board and sensor connections.

---

## **2. Critical Safety Checks First**

Before powering on or plugging in your mouse, verify the following guidelines to protect the delicate microcontroller and motor driver circuitry:

*   **Avoid Multiple USB Connections:** Never plug in more than one USB cable at a time. Only connect to the **ST-Link debugger USB port** (the micro-USB port on the ST-Link programmer board). Plugging in the ST-Link and the processor OTG port simultaneously can cause ground loops and destroy your laptop's USB controllers or the board.
*   **Do Not Force Wheel Rotation:** The wheels are connected to high-ratio gearboxes. Attempting to spin the wheels rapidly by hand will strip the gears and destroy the motor assembly. To test encoders, only rotate them extremely slowly by hand, or roll the mouse gently along a surface.
*   **Do Not Initialize Battery Connection While Powered:** Under normal operation, the battery is plugged into the power board exactly once (during initial assembly) and remains connected. When plugging in the battery connector initially, **ensure the board is completely unpowered (disconnect all USB cables)**. Connecting the battery while the board is powered (e.g., via USB) will cause the onboard charging/boost circuitry to fail catastrophically and can cause the charger chip to catch fire.

---

## **3. Setting Up Python & Installing Dependencies**

Even if you choose to implement your algorithms via the Simulink track, you will still need a local Python installation to run local simulation environments, flash code, and view live serial telemetry.

### **Step 1: Install Python**
Ensure you have Python **3.9** or newer installed:
*   **macOS:** Install Python via [python.org](https://www.python.org/downloads/) or Homebrew (`brew install python`).
*   **Windows:** Install Python via the Microsoft Store or [python.org](https://www.python.org/downloads/). *Ensure you check the box that says **"Add Python to PATH"** during installation.*
*   **Linux:** Installed by default on most distributions. Ensure `python3-pip` is installed (`sudo apt install python3-pip` on Debian/Ubuntu).

### **Step 2: Install Required Libraries**
Install all course python dependencies (e.g., `pyserial`, `pygame`, `mpremote`) using the provided requirements file from your terminal:
```bash
pip install -r python/requirements.txt
```
*(If on Linux/macOS and using multiple versions, you may need to use `pip3` instead of `pip`).*

---

## **4. Flashing the Verification Firmware**

You must load the default verification firmware onto the microcontroller. This firmware is a combined test sketch that executes both a **ToF-to-LED visualization** and a **wall-following safety routine**.

*   **Target Binary:** [pikascript_milestone0.bin](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/binaries/pikascript_milestone0.bin)

### **Flashing Method A: Using `st-flash` Command Line (Recommended)**
Direct SWD flashing via the `st-flash` utility bypasses the ST-Link virtual drive filesystem entirely, preventing any "not enough space" or metadata copy errors.

1.  **Install the ST-Link utility:**
    *   **macOS:** Install via Homebrew: `brew install stlink`
    *   **Linux (Ubuntu/Debian):** `sudo apt install stlink-tools`
    *   **Windows:** Install `pyocd` via pip (`pip install pyocd`) or download the pre-compiled `stlink` Windows binaries and add them to your system Path.
2.  **Flash the binary:**
    Connect the micro-USB cable to the ST-Link programmer board and run the following command from the root of your project directory:
    ```bash
    st-flash --reset write firmware/binaries/pikascript_milestone0.bin 0x08000000
    ```
    *(If using `pyocd` on Windows: `pyocd flash -t stm32f411re firmware/binaries/pikascript_milestone0.bin`)*

### **Flashing Method B: Using STM32CubeProgrammer (GUI)**
1.  Download and install [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html) from STMicroelectronics.
2.  Connect the micro-USB cable to the ST-Link board.
3.  Open the program, select the **ST-LINK** connection interface on the right panel, and click **Connect**.
4.  Navigate to the **Erase & Programming** tab (green checkmark icon).
5.  Browse to select [pikascript_milestone0.bin](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/binaries/pikascript_milestone0.bin) for the **File path**.
6.  Ensure **Start address** is set to `0x08000000` and check **Run after programming**.
7.  Click **Start Programming**.

### **Flashing Method C: USB Drag-and-Drop (Fallback)**
If you copy the binary directly to the mounted USB drive (usually named `NODE_F411RE` or `STLINK`), **do not drag-and-drop using macOS Finder or Windows Explorer**, as the operating system will write hidden metadata files (like `._pikascript_milestone0.bin`) and cause a "not enough space" error. Instead, copy it cleanly via the command line:
*   **macOS:** `cp -X firmware/binaries/pikascript_milestone0.bin /Volumes/NODE_F411RE/`
*   **Linux:** `cp firmware/binaries/pikascript_milestone0.bin /media/*/NODE_F411RE/`
*   **Windows (Command Prompt):** `copy firmware\binaries\pikascript_milestone0.bin D:\` *(replace D:\ with your ST-Link drive letter)*

---

## **5. Power-On & Boot Verification**

Verify the basic electrical, status LED, and sensor feedback:

1.  Disconnect the USB cable.
2.  Place the mouse on a flat surface with walls nearby (e.g. inside a test track lane or near obstacles).
3.  Switch on the main battery slide switch on the power board.
4.  **Confirm Verification Sketch Execution:**
    *   **LED Feedback (ToF Range Test):** Hover your hand close to the left, center, and right sensors. The corresponding onboard status LEDs (Left, Center, and Right) will light up when an obstacle is detected within **200 mm**. (Pins are board-revision dependent: PC13 drives the Left LED, while Center and Right drive pins are routed to PC14/PC15 on legacy boards, or specific analog-capable GPIOs on newer chassis revisions).
    *   **Motor Feedback (Wall Follow & Safe Stop):** Press the **User Button (SW1)** to start the active wall-following test. The mouse will drive forward, using its Time-of-Flight sensors to track and follow the closer wall. As soon as the front sensor detects an obstacle within **150 mm**, the mouse will automatically stop to prevent a collision.
    *   **Steering Dashboard Connectivity:** Because the motor control is gated behind the physical button press, the script remains idle when not actively wall-following. You can plug in the USB cable and run the `steer_mouse.py` tool at any stage (either before pressing SW1, or after the mouse has automatically stopped at a front wall) to manually steer it.
    *   *Optional OLED screen:* If you have attached an optional SSD1306 display, it will also display the "UCT Mouse" splash screen and real-time telemetry (CMD, TOF, BAT, WDG). If no OLED is present, rely on the status LEDs and motor actions.

---

## **6. Running the Keyboard Steering & Telemetry Dashboard**

To verify all sensors (ToF, Gyro, Encoders, Battery) and actuate the motors, use the interactive terminal dashboard:

1.  Place the mouse on a stand (e.g., a small box) so the wheels can spin freely in the air.
2.  Connect the micro-USB cable to the ST-Link debugger port (battery must be **ON**).
3.  Run the keyboard steering dashboard from the project root directory:
    ```bash
    python tools/steer_mouse.py --method serial
    ```
4.  The interactive console dashboard will open. Use the controls below to verify your build:
    *   **Actuation (Motors):** Use the **UP** and **DOWN** arrow keys to command forward and reverse drive. Confirm both wheels spin in the correct directions. Press **SPACE** to stop/brake.
    *   **ToF Sensors:** Wave your hand in front of the Left, Center, and Right Time-of-Flight sensors. Verify that the `ToF Sensors` values update in real-time on the dashboard screen.
    *   **Encoders:** Gently turn the wheels in the air by a fraction of a rotation. Verify that the `Encoders` counts increment/decrement.
    *   **Gyroscope:** Lift the mouse and rotate it in place (yaw). Verify that the `Z` axis on the `IMU Gyro` line fluctuates during rotation.
    *   **Battery:** Verify that the battery voltage reads correctly (approx. 3.7V - 4.2V).
    *   Press **'q'** to exit the dashboard.

---

## **7. Submitting Your Milestone 0 Checkpoint**

To confirm your milestone completion, register your hardware, and prime your account for future autograded submissions, you must submit your telemetry log file:

1.  With the mouse still connected via the ST-Link USB cable, run the log extraction tool from the project root:
    ```bash
    python tools/dump_logs.py
    ```
2.  This command captures the internal hardware run logs and saves a file named `run_log.jsonl` in your project folder.
3.  Submit `run_log.jsonl` to the **Milestone 0 Gradescope Assignment**.
4.  **The Gradescope Autograder will verify:**
    *   The log contains a valid header file.
    *   The 96-bit Unique Device ID (UID) of your microcontroller is successfully parsed and registered to your student profile (which binds your specific board to your account for plagiarism audits on later milestones).
    *   Sensors and encoders show active reading fluctuations, proving your build is functional.

---

## **8. Next Steps: Choosing a Firmware & Getting Started**

Once your hardware is verified and Milestone 0 is submitted, you are ready to transition to developing control algorithms for Milestone 1. 

Choose your development track and refer to the specific guides for detailed "getting started" and setup instructions:

*   **The Master Guide:** Refer to the **[Student Workflow Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md)** for detailed installation steps, workspace structure (`workspace/` directory), and compilation commands.
*   **If you choose the MicroPython Track:** Follow the setup in the Student Workflow Guide to flash `micropython.bin` and deploy your scripts dynamically using the VCP CLI deployer:
    ```bash
    python tools/deploy.py --engine micropython --script workspace/task1_square/run_square.py
    ```
*   **If you choose the PikaScript Track:** Follow the workflow instructions to embed Python logic directly into the C-Kernel binaries.
*   **If you choose the Simulink Track:** Open the model template `matlab/simulink/StudentTemplate.slx` and consult the **[Simulink Development & Autograding Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/simulink_guide.md)** to configure C-Coder wrappers and launch desktop Pygame loopback co-simulations.

A complete directory of all project resources is available in the **[Documentation Index (docs/README.md)](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/README.md)**.

