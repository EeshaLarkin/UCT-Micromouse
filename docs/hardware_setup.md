# Hardware Setup & Calibration Guide

This guide details the physical hardware configuration, known hardware issues (such as the silicon speed lottery), and calibration procedures for the UCT Micromouse.

> [!WARNING]
> **CRITICAL HARDWARE SAFETY WARNINGS:**
> *   **AVOID MULTIPLE USB CONNECTIONS:** To protect your hardware (microcontroller, power board, and laptop/charger) from damage due to ground loops or power contention, **NEVER PLUG IN MORE THAN ONE USB CABLE AT A TIME.** Do not simultaneously connect USB cables to the power board, the processor board, and the ST-Link debugger. Always use a single cable connected to the ST-Link debugger port.
> *   **DO NOT TURN WHEELS MANUALLY:** The wheels are connected to a high-ratio gearbox. Rotating the wheels externally by hand is highly likely to strip the gears and permanently destroy the motor assembly.
> *   **DO NOT CONNECT BATTERY WHILE USB IS ATTACHED:** Never plug the battery into the main power board while any USB cables are connected to the mouse. Doing so can cause catastrophic failure of the onboard boost converter.

---

## 1. Electrical & Peripheral Configuration

The Micromouse is built around an STM32 micro-controller board routing sensor arrays to user logic:

*   **Motors:** Brushed DC motors driven via H-bridge controllers. Handled via standard PWM timers.
*   **Time-of-Flight (ToF):** 3x VL53L0X I2C distance sensors (Left, Center, Right).
*   **Encoders:** Quadrature wheel encoders reporting pulse counts to the timer counter register to track mouse telemetry.
*   **Battery Monitoring & Current Sensing:** INA219 current/power monitor or ADC configuration providing real-time bidirectional current and voltage tracking. Negative current values are fully supported and represent reverse current flow.
*   **IMU Gyroscope:** Integrated I2C IMU to monitor yaw angular velocity.
*   **Display:** SSD1306 I2C OLED display indicating system state, battery levels, sensor distances, and error states.
*   **Onboard LEDs:** Three hardware-identical LEDs (LED0 on `PC13`, LED1 on `PC14`, LED2 on `PC15`) electrically gated by pin `PB3` (`CTRL_LEDS`). Pin `PB3` must be written `HIGH` to enable any of the LEDs.

---

## 2. Hardware Safety Guard: Watchdog Timer

To prevent damage to the physical testbed, the C-Kernel implements a **1000 ms Watchdog Safety Timer**:
*   The C-Kernel tracks elapsed time since the last packet was successfully decoded.
*   If no commands arrive within 1000 ms, the motor driver enable pin is asserted low (`HAL_GPIO_WritePin(MOTOR_EN_GPIO_Port, MOTOR_EN_Pin, GPIO_PIN_RESET)`), cutting power to the motors.
*   The watchdog is reset immediately upon receiving any valid downlink command (`{"a":...}`, `{"p":1}`, etc.).

---

## 3. The 72 MHz vs 80 MHz Silicon Lottery

Due to component supply variance and factory calibration differences, some microcontroller boards run their internal PLL loop at `80 MHz` (the design target), while others only boot at `72 MHz`.

### Impact on Serial Communication
An incorrect clock rate changes the peripheral clock bus frequency, which throws off the UART baud rate calculation:
*   A board running at `72 MHz` configured for `80 MHz` will suffer a ~11% baud rate mismatch, rendering serial communication completely garbled or unresponsive.

### Diagnostic & Fix
*   **Target Divider (`80 MHz`):** Uses register value `USART1->BRR = 694` for standard 115200 baud communication.
*   **Outlier Divider (`72 MHz`):** Uses register value `USART1->BRR = 625` to achieve 115200 baud.
*   **Action:** If a board fails to connect to the Python dashboard and shows timeouts or corrupt symbols, but works when the register divider in the firmware configuration is modified to `625`, the microcontroller is a 72 MHz outlier and should be labeled as such.

---

## 4. Motor Polarity Calibration

Depending on student assembly and motor lead soldering, one or both motors may run in reverse relative to the command values.

### Calibration Multipliers
To keep userland solver code unified, calibration must happen at the Kernel level rather than the control algorithm level:
*   Modify `polarity_l` and `polarity_r` variables (set to `1` or `-1`) in [micromouse_kernel.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/src/kernel/src/micromouse_kernel.c).
*   This normalizes commands so that positive values (e.g. `set_motors(50, 50)`) always translate to forward motion on both wheels.

---

## 5. Signed 8-bit `abs()` Casting Workaround

Older ARM GCC compiler versions sometimes miscompile signed 8-bit negative casts inside standard `<stdlib.h>` `abs()` operations. When reversing, the sign bit can get mangled, locking the motor. 
*   **Kernel Fix:** The kernel bypasses `abs()` directly by checking motor direction checks explicitly, assigning the absolute values natively:
    ```c
    if (actual_l >= 0) {
        TIM3->CCR3 = actual_l;
        TIM3->CCR4 = 0;
    } else {
        TIM3->CCR3 = 0;
        TIM3->CCR4 = -actual_l;
    }
    ```
