# =========================================================================
# UCT Micromouse - Tier 2 Python PC Mock Wrapper
# =========================================================================
# This module perfectly mimics the hardware PikaScript uct_mouse API.
# When students run main.py on their PC, this silently connects to the 
# Simulink TCP Virtual Testbed instead of physical hardware!
# =========================================================================

import time
from micromouse import Micromouse

# Create a global background TCP instance
_mouse = Micromouse(method='tcp', verbose=False)

def init():
    """Connects to the Simulink Autograder and configures lock-step time."""
    try:
        _mouse.connect()
        # Lock simulation physics to 20Hz (0.05s steps) to match Python loop
        _mouse.configure(rate=20, sync=1)
        print("[PC Mock] Connected to Simulink Virtual Testbed.")
        return True
    except Exception as e:
        print(f"[PC Mock] Connection failed: {e}")
        return False

def set_motors(left_pwm, right_pwm):
    """Sends motor commands to the virtual physics engine."""
    _mouse.set_pwm(int(left_pwm), int(right_pwm))

def get_tof():
    """Returns (left, center, right) virtual ToF distances in mm."""
    s = _mouse.get_sensors()
    return s.get('tof_l', 0), s.get('tof_c', 0), s.get('tof_r', 0)

def get_encoders():
    """Returns (left, right) virtual encoder ticks."""
    s = _mouse.get_sensors()
    return s.get('lenc', 0), s.get('renc', 0)

def get_vbatt():
    """Returns virtual battery voltage."""
    s = _mouse.get_sensors()
    return s.get('v_batt', 0.0)

def delay_ms(ms):
    """Pauses the Python thread (Simulink physics clock will pause and wait)."""
    time.sleep(ms / 1000.0)