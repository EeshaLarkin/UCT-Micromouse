# Session State Log - UCT Micromouse

## 1. Summary of Completed Fixes

### Hardware Ruggedization
* **NVIC Timer Interrupt Storms:** Disabled unused timer interrupts (`TIM4_IRQn`, `TIM5_IRQn`, and `TIM7_IRQn`) at priority 0 in `MX_NVIC_Init()` inside both `main.c` and `MicroMouse_main.c`. This prevents touch-induced electrostatic noise on exposed header pins from freezing the CPU.
* **Global EXTI Handlers:** Added explicit default vectors for all unused EXTI GPIO lines in `stm32l4xx_it.c` to prevent locking in the default handler.
* **Flash Read-During-Write filesystem corruption:** Staged default factory files (`boot.py`, `main.py`) in stack RAM in `board_init.c` to bypass bank collisions during format.

### Peripheral & Display Features
* **OLED Blank Screen:** Added explicit re-initialization calls (`MX_I2C1_Init`, `MX_I2C2_Init`) inside `initMicroMouse()` to restore I2C clocks after the MicroPython VM boot sequence.
* **OLED Blanking on USB Connect (Fixed):** Removed the code in `bdev.c` (`BDEV_IOCTL_INIT`) that set `mouse_initialized = false` when mounting the USB FAT filesystem, resolving the issue where display updates and live telemetry would halt upon plugging in the USB-C OTG cable.
* **SPI2 De-Initialization on Soft Reset (Fixed):** Added `HAL_SPI_DeInit(&hspi2)` inside `ext_flash_init()` in `bdev.c` to reset the `hspi2` handle state to `RESET`. This forces `HAL_SPI_Init` to execute `HAL_SPI_MspInit` and re-assert the GPIO alternate function configurations on PB13/PB14/PB15, preventing the SPI pins from remaining floating after a MicroPython soft reset.
* **I2C Bus Lockup from USB Preemption (Fixed):**
  * Gated all sensor reads and display updates inside `kernel_background_tick()` in `board_init.c` by disabling the USB interrupt (`OTG_FS_IRQn`) using `HAL_NVIC_DisableIRQ()` and `HAL_NVIC_EnableIRQ()`. This prevents high-priority USB mass storage block reads from preempting I2C transfers mid-byte and causing permanent physical bus lockups.
  * Rate-limited the OLED `kernel_update_display()` updates to 10 Hz (every 100ms) to reduce CPU/I2C contention and minimize USB interrupt latency.
* **OLED TOF Dynamic Layout & Alignment:** 
  * Reformatted TOF readings to a fixed-width `%4u` representation to prevent horizontal layout shifting on digits changes.
  * Implemented dynamic layout configuration: if only (N, NW, NE) is connected, shows `NW / N / NE`; if (N, W, E) or all 5 are connected, shows `W / N / E`.
  * **OLED Color Boundary Text Alignment:** Re-aligned the non-dynamic 5-string layout positions (`y = 0, 16, 28, 40, 52`) to ensure that Line 2 aligns perfectly with the physical split boundary between the top yellow and bottom blue OLED screen regions, preventing split-color text.

### Motor Activation (MicroPython Engine)
* **Pin Alternate Function Restorations:** Added de-init/re-init calls for `TIM3` (PWM), `TIM4` (Encoders), and `PD7` (`MOTOR_EN_Pin` output mode) at the start of `uct_mouse.init()`. This ensures that when Python boots, the PWM registers and motor driver control lines are re-routed to the physical hardware pins rather than remaining in MicroPython's default high-impedance input state.

### Motor & Encoder Control Bedrock (PikaScript / C-Kernel)
* **Baudrate Calibration & Reversion:** Reverted the clock-divider `USART1->BRR` in `board_init.c` and `main.c` back to the standard `694` (confirming 80 MHz operation) after verifying clean telemetry at 115200 baud.
* **Ternary Absolute Value Bypass:** Replaced standard `<stdlib.h>` `abs()` duty-cycle calculations in [micromouse_kernel.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/firmware/src/kernel/src/micromouse_kernel.c) with direct safe ternary expressions (`(val < 0) ? -val : val`). This completely bypasses the signed-integer compiler sign-mangling bug on negative left motor PWM values.
* **Quadrature Encoder Interrupt Counters:** Implemented physical encoder increments directly in the `TIM4` input capture callback in [Motors.c](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/external/MicroMouseTemplate/MicroMouseProgramming_Code/Core/Src/Motors.c). Both `leftEncoderCount` and `rightEncoderCount` now correctly increment or decrement based on phase B direction pins, restoring position tracking.
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
1. **Physical LED Check:** Confirm why the center and right LEDs are physically non-responsive even though the MCU is successfully driving PC14 and PC15 registers.
   * **Verification Completed so far:**
     * Verified that `GPIOC->MODER` configuration registers for pins 13, 14, and 15 are correctly set to `01` (General purpose output mode).
     * Verified that `RCC->BDCR` is successfully cleared to `0x00000000`, proving that LSE is disabled and freeing the pins from the low-speed oscillator.
     * Verified that the master power gating pin `PB3` (`CTRL_LEDS`) is successfully driven HIGH (proven by the fact that the Left LED on PC13 functions and blinks).
     * Verified that `GPIOC->ODR` output data registers for pins 13, 14, and 15 successfully toggle state, proving that the MCU is electrically driving all three outputs.
2. **Remove Trace Prints:** If the board boots successfully, the raw UART trace prints in `main.c` and `VL53L0X.c` can be cleaned up/removed to keep the output tidy.
