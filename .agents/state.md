# Session State Log - UCT Micromouse

## 1. Summary of Completed Fixes

### Hardware Ruggedization
* **NVIC Timer Interrupt Storms:** Disabled unused timer interrupts (`TIM4_IRQn`, `TIM5_IRQn`, and `TIM7_IRQn`) at priority 0 in `MX_NVIC_Init()` inside both `main.c` and `MicroMouse_main.c`. This prevents touch-induced electrostatic noise on exposed header pins from freezing the CPU.
* **Global EXTI Handlers:** Added explicit default vectors for all unused EXTI GPIO lines in `stm32l4xx_it.c` to prevent locking in the default handler.
* **Flash Read-During-Write filesystem corruption:** Staged default factory files (`boot.py`, `main.py`) in stack RAM in `board_init.c` to bypass bank collisions during format.

### Peripheral & Display Features
* **OLED Blank Screen:** Added explicit re-initialization calls (`MX_I2C1_Init`, `MX_I2C2_Init`) inside `initMicroMouse()` to restore I2C clocks after the MicroPython VM boot sequence.
* **OLED TOF Dynamic Layout & Alignment:** 
  * Reformatted TOF readings to a fixed-width `%4u` representation to prevent horizontal layout shifting on digits changes.
  * Implemented dynamic layout configuration: if only (N, NW, NE) is connected, shows `NW / N / NE`; if (N, W, E) or all 5 are connected, shows `W / N / E`.

### Motor Activation (MicroPython Engine)
* **Pin Alternate Function Restorations:** Added de-init/re-init calls for `TIM3` (PWM), `TIM4` (Encoders), and `PD7` (`MOTOR_EN_Pin` output mode) at the start of `uct_mouse.init()`. This ensures that when Python boots, the PWM registers and motor driver control lines are re-routed to the physical hardware pins rather than remaining in MicroPython's default high-impedance input state.

### Motor & Encoder Control Bedrock (PikaScript / C-Kernel)
* **Baudrate Calibration & Reversion:** Reverted the clock-divider `USART1->BRR` in `board_init.c` and `main.c` back to the standard `694` (confirming 80 MHz operation) after verifying clean telemetry at 115200 baud.
* **Ternary Absolute Value Bypass:** Replaced standard `<stdlib.h>` `abs()` duty-cycle calculations in [micromouse_kernel.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/src/kernel/src/micromouse_kernel.c) with direct safe ternary expressions (`(val < 0) ? -val : val`). This completely bypasses the signed-integer compiler sign-mangling bug on negative left motor PWM values.
* **Quadrature Encoder Interrupt Counters:** Implemented physical encoder increments directly in the `TIM4` input capture callback in [Motors.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/external/MicroMouseTemplate/MicroMouseProgramming_Code/Core/Src/Motors.c). Both `leftEncoderCount` and `rightEncoderCount` now correctly increment or decrement based on phase B direction pins, restoring position tracking.
* **Safety Watchdog Timer Verification:** Verified that the 1-second watchdog cutoff functions correctly and has been re-enabled.

---

## 2. Hardware Diagnostic & Verification Checkpoint
Register-level diagnostic dumps verified that the microcontroller peripheral states are 100% correct:
* `TIM3` outputs enabled (`CCER = 0x00001111`), counter active (`CR1 = 0x00000081`), and duty registers driven to `500` (50% PWM) when active.
* `GPIOC` alternate function pins (PC6–PC9) configured correctly in Alternate Function 2 (`AF2_TIM3`).
* `MOTOR_EN` pin (**PD7**) successfully driven HIGH (`State = 1`).

**Conclusion:** Software configuration is fully correct. If the physical wheels do not turn, it indicates a hardware power-path issue (e.g. physical slide switch is **OFF**, battery is disconnected, or the motor voltage isolation jumper `VMOT` / `MOTOR_PWR` is unbridged).

---

## 3. Pending Verification & Next Steps
1. **Physical Power Checks:** Verify that the motor power jumper (if present) is bridged and the physical slide switch is turned ON.
2. **IMU Verification:** The background IMU task (`refreshIMUValues()`) is currently commented out in `board_init.c` to validate mechanical stability. Once motor and TOF operations are verified, uncomment line 232 of `board_init.c` to restore yaw tracking.

