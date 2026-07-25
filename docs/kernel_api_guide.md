# Micromouse Python API Reference Guide

This document defines the high-level Python API (`uct_mouse` module) used by students for both desktop simulation testing and physical STM32 hardware execution.

---

## 1. The `uct_mouse` Python Module

Students interact with the hardware and simulation environment strictly through the built-in `uct_mouse` library.

### API Methods Reference

| Method | Parameters | Return Value | Description |
|---|---|---|---|
| `init` | `fast_sim=None` *(bool)* | `int` | Initializes connection to either the virtual simulation testbed (PC) or the physical hardware (STM32). |
| `set_motors` | `left_pwm` *(int)*, `right_pwm` *(int)* | `None` | Sets raw motor speeds. Speeds range from `-100` (full reverse) to `100` (full forward). |
| `get_tof` | None | `(left, front_left, center, front_right, right)` *(tuple of ints)* | Returns current VL53L0X distance readings in millimeters (0–8190 mm). `8190` represents out-of-range or disconnected. |
| `get_encoders` | None | `(left, right)` *(tuple of ints)* | Returns total accumulated quadrature encoder ticks. |
| `get_gyro` | None | `float` | Returns current yaw gyro rate/angle (relative degrees/second rotation around Z-axis). |
| `get_vbatt` | None | `float` | Returns current battery supply voltage in Volts. |
| `delay_ms` | `ms` *(int)* | `None` | Delays execution. **CRITICAL:** On physical hardware, sensor/display updates are paced inside this call; control loops must call this to update values. |
| `set_polarity` | `left` *(int)*, `right` *(int)* | `None` | Normalizes physical motor wiring. Pass `1` (normal) or `-1` (reversed) to mathematically match your chassis. |
| `get_line_sensors`| None | `(fl, fr, sl, sr)` *(tuple of ints)* | Returns raw ADC readings for Front-Left, Front-Right, Side-Left, and Side-Right photodetector line sensors. |
| `get_telemetry` | None | `(ax, ay, az, gx, gy, gz, lenc, renc, current, battery_pct)` *(tuple)* | Returns full 6-DOF IMU data (ax/ay/az in m/s², gx/gy/gz in rad/s), encoders, battery current (mA), and battery life (%). |

---

## 2. Dynamic OLED Display Modes

On physical hardware, the C-Kernel automatically manages the SSD1306 OLED display configuration based on connected hardware:

* **3-Sensor Combination (N, W, E):** If only the Left, Centre, and Right TOF sensors are connected, the display shows:
  `W:[W_val] N:[N_val] E:[E_val]`
* **3-Sensor Combination (N, NW, NE):** If only the Front-Left, Centre, and Front-Right TOF sensors are connected, the display shows:
  `NW:[FL_val] N:[C_val] NE:[FR_val]`
* **5-Sensor Combination (All Connected):** If all 5 sensors are connected, the OLED defaults to displaying the **(N, W, E)** subset.
* **All values are right-aligned to a 4-character fixed-width field** (`%4u`) to prevent horizontal layout shifting.
