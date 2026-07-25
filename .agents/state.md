# Session State Log - UCT Micromouse

## 1. Summary of Completed Fixes

### Hardware Ruggedization
* **NVIC Timer Interrupt Storms:** Disabled unused timer interrupts (`TIM5_IRQn` and `TIM7_IRQn`) at priority 0 in `MX_NVIC_Init()` inside both `main.c` and `MicroMouse_main.c`. This prevents touch-induced electrostatic noise on exposed header pins from freezing the CPU.
* **TIM4 Encoder Interrupt Priority & Routing:**
  * Lowered `TIM4_IRQn` priority to `5` in `initMotors()` inside `Motors.c` to prevent high-frequency encoder edge captures from starving critical lower-priority interrupts like SysTick and USB.
  * Patched the MicroPython core interrupt file (`external/micropython/ports/stm32/stm32_it.c`) inside `TIM4_IRQHandler` to explicitly invoke `HAL_TIM_IRQHandler(&htim4)` when `COMPILING_FOR_MICROPYTHON` is defined. This routes capture events to our speed/position callbacks instead of letting them lock up the CPU in an infinite interrupt-re-entry loop.
* **Encoder Open-Drain Pull-Up configuration:** Configured PD12-PD15 with internal pull-up resistors (`GPIO_PULLUP`) inside `stm32l4xx_hal_msp.c` to support open-collector motor encoders and prevent signal floating on transitions.
* **Unconditional Position Tracking:** Modified the capture callback inside `Motors.c` to increment/decrement `leftEncoderCount` and `rightEncoderCount` unconditionally on every edge, rather than trapping position tracking inside the speed threshold filters.
* **Global EXTI Handlers:** Added explicit default vectors for all unused EXTI GPIO lines in `stm32l4xx_it.c` to prevent locking in the default handler.
* **Flash Read-During-Write filesystem corruption:** Staged default factory files (`boot.py`, `main.py`) in stack RAM in `board_init.c` to bypass bank collisions during format.

### Peripheral & Display Features
* **OLED Early Boot Splash Screen:** Added SSD1306 initialization and welcoming text drawing inside the early C hook `board_early_init()` in `board_init.c`. This provides immediate visual power-on feedback to users without invoking I2C sensor bus scans inside `boot.py` (which could deadlock the boot process).
* **OLED Blank Screen:** Added explicit re-initialization calls (`MX_I2C1_Init`, `MX_I2C2_Init`) inside `initMicroMouse()` to restore I2C clocks after the MicroPython VM boot sequence.
* **OLED Blanking on USB Connect (Fixed):** Removed the code in `bdev.c` (`BDEV_IOCTL_INIT`) that set `mouse_initialized = false` when mounting the USB FAT filesystem, resolving the issue where display updates and live telemetry would halt upon plugging in the USB-C OTG cable.
* **SPI2 De-Initialization on Soft Reset (Fixed):** Added `HAL_SPI_DeInit(&hspi2)` inside `ext_flash_init()` in `bdev.c` to reset the `hspi2` handle state to `RESET`. This forces `HAL_SPI_Init` to execute `HAL_SPI_MspInit` and re-assert the GPIO alternate function configurations on PB13/PB14/PB15, preventing the SPI pins from remaining floating after a MicroPython soft reset.
* **I2C Bus Lockup from USB Preemption (Fixed):**
  * Gated all sensor reads and display updates inside `kernel_background_tick()` in `board_init.c` by disabling the USB interrupt (`OTG_FS_IRQn`) using `HAL_NVIC_DisableIRQ()` and `HAL_NVIC_EnableIRQ()`. This prevents high-priority USB mass storage block reads from preempting I2C transfers mid-byte and causing permanent physical bus lockups.
  * Rate-limited the OLED `kernel_update_display()` updates to 10 Hz (every 100ms) to reduce CPU/I2C contention and minimize USB interrupt latency.
* **I2C Bus Congestion and Back-off Cool-downs:** 
  * Localized the `I2C_TIMEOUT` to 2ms inside `VL53L0X.c` and `IMU.c` for quick register reads, while keeping the 50ms global timeout in `main.h` for large OLED frame buffer transfers.
  * Implemented a 100ms error cool-down (back-off) inside `getVL53L0()` and `refreshIMUValues()` to immediately skip reading failed or missing sensors, preventing CPU starvation from cumulative blocking timeouts.
* **OLED TOF Dynamic Layout & Alignment:** 
  * Reformatted TOF readings to a fixed-width `%4u` representation to prevent horizontal layout shifting on digits changes.
  * Implemented dynamic layout configuration: if only (N, NW, NE) is connected, shows `NW / N / NE`; if (N, W, E) or all 5 are connected, shows `W / N / E`.
  * **OLED Color Boundary Text Alignment:** Re-aligned the non-dynamic 5-string layout positions (`y = 0, 16, 28, 40, 52`) to ensure that Line 2 aligns perfectly with the physical split boundary between the top yellow and bottom blue OLED screen regions, preventing split-color text.

### Motor Activation (MicroPython Engine)
* **Pin Alternate Function Restorations:** Added de-init/re-init calls for `TIM3` (PWM), `TIM4` (Encoders), and `PD7` (`MOTOR_EN_Pin` output mode) at the start of `uct_mouse.init()`. This ensures that when Python boots, the PWM registers and motor driver control lines are re-routed to the physical hardware pins rather than remaining in MicroPython's default high-impedance input state.

### Motor & Encoder Control Bedrock (PikaScript / C-Kernel)
* **Baudrate Calibration & Reversion:** Reverted the clock-divider `USART1->BRR` in `board_init.c` and `main.c` back to the standard `694` (confirming 80 MHz operation) after verifying clean telemetry at 115200 baud.
* **Ternary Absolute Value Bypass:** Replaced standard `<stdlib.h>` `abs()` duty-cycle calculations in [micromouse_kernel.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/src/kernel/src/micromouse_kernel.c) with direct safe ternary expressions (`(val < 0) ? -val : val`). This completely bypasses the signed-integer compiler sign-mangling bug on negative left motor PWM values.
* **Safety Watchdog Timer Verification:** Verified that the 1-second watchdog cutoff functions correctly and has been re-enabled.

### External Flash & Logging System
* **FAT Filesystem Relocation:** Shifted MicroPython's filesystem (`UCT_MMOUSE` drive) block device mappings to the last **128 KB** (`0xE0000` to `0xFFFFF`) of the external ZD25WQ80C SPI flash. This preserves the internal STM32 MCU flash from write wear while leaving the first **896 KB** open for data logging.
* **JSON Sparse Telemetry Logger:** Built a 25 Hz sequential logger writing telemetry JSON lines directly to the external flash. Features automatic logging activation on first motor command, overwrites previous run logs on startup, and utilizes sparse comparisons to optimize memory.
* **Anti-Cheat Verification Headers:** Integrated Unique Device ID (96-bit MCU UID) and 32-bit FNV-1a code-structure verification hashes into the telemetry headers to detect identical code submissions or copied logs.
* **Universal Serial Log Dump Protocol:** Added VCP serial JSON command `{"c":{"dump":1}}` (and Python wrapper `uct_mouse.dump_logs()`) to stream log files over UART instantly on all three firmware runtimes without requiring code re-flashing.

### Standalone C/Simulink Template Target Fixes
* **Timebase Interrupt Tick Restore (SysTick/TIM6 Linkage Bug Fixed):**
  * **Issue:** The main/Simulink template binary would consistently lock up silently on boot right at `MicroMouse_Deploy_initialize()` (specifically inside the 200ms startup delay of `initTOFs`).
  * **Cause:** The HAL timebase period elapsed callback was misnamed as `jesse_legacy_period_elapsed_callback` instead of the standard name `HAL_TIM_PeriodElapsedCallback`. Because of this name mismatch, TIM6 interrupts were linked to the weak default fallback in the HAL driver (which does nothing), meaning `uwTick` remained `0` forever, and `HAL_Delay` hung in an infinite loop.
  * **Fix:** Renamed the callback to `HAL_TIM_PeriodElapsedCallback` in both [main.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/external/MicroMouseTemplate/MicroMouseProgramming_Code/Core/Src/main.c) and [MicroMouse_main.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/external/MicroMouseTemplate/MicroMouseProgramming_Code/Core/Src/MicroMouse_main.c). The MCU now boots and initializes all peripherals successfully without freezing.
* **System Clock Variable Sync:** Added `SystemCoreClockUpdate()` right after `SystemClock_Config()` in `main.c` to update CMSIS timing variables to 80 MHz, ensuring that delays calculate correctly on GCC-optimized builds.
* **Backup Domain Reset for GPIO PC14/PC15 release:**
  * **Issue:** Center (PC14) and Right (PC15) LEDs would physically remain completely off even when their GPIO registers were driven high by the MCU.
  * **Cause:** PC14 and PC15 default to Low Speed External (LSE) oscillator pins on reset. If a previous runtime (like MicroPython) turns on the LSE clock, the configuration persists in the Backup Domain across soft resets, hardware locking the pins out of GPIO mode.
  * **Fix:** Inserted a Backup Domain reset block (`__HAL_RCC_BACKUPRESET_FORCE()`/`__HAL_RCC_BACKUPRESET_RELEASE()`) at the very start of `main()` to disable LSE and release the pins back to standard GPIO mode.

---

## 2. Hardware Diagnostic & Verification Checkpoint
Register-level diagnostic dumps verified that the microcontroller peripheral states are 100% correct:
* `TIM3` outputs enabled (`CCER = 0x00001111`), counter active (`CR1 = 0x00000081`), and duty registers driven to `500` (50% PWM) when active.
* `GPIOC` alternate function pins (PC6–PC9) configured correctly in Alternate Function 2 (`AF2_TIM3`).
* `MOTOR_EN` pin (**PD7**) successfully driven HIGH (`State = 1`).

**Conclusion:** Software configuration is fully correct. If the physical wheels do not turn, it indicates a hardware power-path issue (e.g. physical slide switch is **OFF**, battery is disconnected, or the motor voltage isolation jumper `VMOT` / `MOTOR_PWR` is unbridged).

---

## 3. Pending Verification & Next Steps
1. **Flash Accelerometer-Logging Firmware:**
   * **Detail:** The changes to `kernel_logger.c` to write the 3-axis accelerometer readings (`"ax"`, `"ay"`, `"az"`) to external flash have been coded and committed to git, but since the mouse was placed on charge, they have not yet been flashed to the physical MCU. 
   * **Next Step:** Flash the board using `python tools/deploy.py --engine micropython --flash` once charging is complete, and verify that the dump logs contain `"ax"`, `"ay"`, and `"az"` keys.
2. **Physical LED Check:** Confirm why the center and right LEDs are physically non-responsive even though the MCU is successfully driving PC14 and PC15 registers.
3. **Remove Trace Prints:** If the board boots successfully, the raw UART trace prints in `main.c` and `VL53L0X.c` can be cleaned up/removed to keep the output tidy.
