# =========================================================================
# UCT Micromouse - Tier 2 Python PC Mock Wrapper
# =========================================================================
# This module perfectly mimics the hardware PikaScript uct_mouse API.
# When students run main.py on their PC, this silently connects to the 
# Simulink TCP Virtual Testbed instead of physical hardware!
# =========================================================================

import time
import os
import sys
import json
import socket
import subprocess
import atexit
from micromouse import Micromouse

# Resolve configuration file paths
_script_dir = os.path.dirname(os.path.abspath(__file__))
_config_path = os.path.join(_script_dir, "sim_config.json")

# Track the auto-started simulator process
_backend_process = None

def _is_port_active(host="127.0.0.1", port=8000):
    """Checks if a TCP port is active (listening) on localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.1)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def _cleanup_backend():
    """Terminate the auto-started simulator process on exit."""
    global _backend_process
    if _backend_process is not None:
        try:
            _backend_process.terminate()
            _backend_process.wait(timeout=1.0)
        except Exception:
            try:
                _backend_process.kill()
            except Exception:
                pass
        _backend_process = None

# Create a global background TCP instance
_mouse = Micromouse(method='tcp', verbose=False)
_pending_pwm_l = 0
_pending_pwm_r = 0
_pwm_dirty = False

def init():
    """Connects to the configured simulation backend, auto-starting if enabled."""
    global _backend_process
    
    # Default configuration
    config = {
        "backend": "simulink",
        "auto_start": False,
        "map": "empty",
        "imbalance": 0.08,
        "slip": 0.08,
        "video": ""
    }
    
    # Load local config overrides if present
    if os.path.exists(_config_path):
        try:
            with open(_config_path, "r") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"[PC Mock] Warning: Failed to read {os.path.basename(_config_path)}: {e}")
            
    # Force auto_start = False if running under Gradescope Autograder
    if os.environ.get("GRADESCOPE_AUTOGRADER") == "1":
        config["auto_start"] = False

    backend = config.get("backend", "simulink").lower()
    auto_start = config.get("auto_start", False)
    
    # Attempt to connect to an already running simulator on port 8000
    connected_sock = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        s.connect(("127.0.0.1", 8000))
        s.settimeout(None)
        connected_sock = s
    except Exception:
        pass  # No server running, or connection timed out/refused
        
    auto_started = False
    if connected_sock is None:
        if backend == "python" and auto_start:
            sim_script = os.path.join(os.path.dirname(_script_dir), "tools", "physics_sim.py")
            if os.path.exists(sim_script):
                # Construct physics_sim command line arguments from config
                cmd = [sys.executable, sim_script]
                if "map" in config:
                    cmd += ["--map", str(config["map"])]
                if "seed" in config and config["seed"] is not None:
                    cmd += ["--seed", str(config["seed"])]
                if "imbalance" in config:
                    cmd += ["--imbalance", str(config["imbalance"])]
                if "slip" in config:
                    cmd += ["--slip", str(config["slip"])]
                if "video" in config and config["video"]:
                    cmd += ["--video", str(config["video"])]
                    
                print(f"[PC Mock] Auto-starting Python Physics Simulator...")
                try:
                    # Spawn the simulator process
                    _backend_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    # Register exit handler to clean up when main process exits
                    atexit.register(_cleanup_backend)
                    
                    # Poll port 8000 until active
                    for _ in range(30):  # Wait up to 1.5 seconds
                        time.sleep(0.05)
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(0.1)
                            s.connect(("127.0.0.1", 8000))
                            s.settimeout(None)
                            connected_sock = s
                            auto_started = True
                            break
                        except Exception:
                            pass
                    if connected_sock is None:
                        print("[PC Mock] Error: Python simulator started but port 8000 did not become active.")
                except Exception as e:
                    print(f"[PC Mock] Error spawning simulator: {e}")
            else:
                print(f"[PC Mock] Error: Simulator script not found at {sim_script}")
        else:
            if backend == "simulink":
                print("[PC Mock] Waiting for Simulink Virtual Testbed...")
                print("[PC Mock] Please open MATLAB and run matlab/simulink/launch_virtual_testbed.m")
                # Fall back to standard connect which has a retry loop and prints messages
                try:
                    _mouse.connect()
                    # Lock simulation physics to 100Hz (0.01s steps) to match Python loop
                    _mouse.configure(rate=100, sync=1)
                    print("[PC Mock] Connected to Simulink Virtual Testbed.")
                    return True
                except Exception as e:
                    print(f"[PC Mock] Connection failed: {e}")
                    print("[PC Mock] Hint: Make sure Simulink Virtual Testbed is running in MATLAB.")
                    return False
            else:
                print("[PC Mock] No active server on port 8000. Ensure simulator is running.")
                return False
                
    if connected_sock is not None:
        try:
            # Bind the successfully connected socket to the Micromouse instance
            _mouse.sock = connected_sock
            _mouse.connected = True
            _mouse.configure(rate=100, sync=1)
            
            if backend == "python":
                if auto_started:
                    print("[PC Mock] Connected to Python Physics Simulator (Auto-started).")
                else:
                    print("[PC Mock] Connected to Python Physics Simulator (Pre-running).")
            else:
                print("[PC Mock] Connected to Simulink Virtual Testbed.")
            return True
        except Exception as e:
            print(f"[PC Mock] Connection initialization failed: {e}")
            return False
    else:
        return False

def set_motors(left_pwm, right_pwm):
    """Sends motor commands to the virtual physics engine without instantly advancing time."""
    global _pending_pwm_l, _pending_pwm_r, _pwm_dirty
    _pending_pwm_l = int(left_pwm)
    _pending_pwm_r = int(right_pwm)
    _pwm_dirty = True
    # We do NOT immediately exchange data here. delay_ms will pace the simulation.

def get_tof():
    """Returns (left, center, right) virtual ToF distances in mm."""
    s = _mouse.get_sensors()
    return s.get('tof_l', 0), s.get('tof_c', 0), s.get('tof_r', 0)

def get_gyro():
    """Returns virtual gyro reading (yaw rate or angle depending on context, typically deg/s or relative heading)."""
    s = _mouse.get_sensors()
    return s.get('gyro', 0.0)

def get_encoders():
    """Returns (left, right) virtual encoder ticks."""
    s = _mouse.get_sensors()
    return s.get('lenc', 0), s.get('renc', 0)

def get_vbatt():
    """Returns virtual battery voltage."""
    s = _mouse.get_sensors()
    return s.get('v_batt', 0.0)

def delay_ms(ms):
    """Pauses the Python thread while advancing simulator physics in lock-step."""
    global _pwm_dirty
    rate_hz = 100  # Sync rate: 100Hz (10ms steps)
    step_ms = 1000.0 / rate_hz
    steps = int(ms / step_ms)
    
    if steps <= 0:
        time.sleep(ms / 1000.0)
        return
        
    for _ in range(steps):
        if _mouse.connected:
            try:
                if _pwm_dirty:
                    _mouse.set_pwm(_pending_pwm_l, _pending_pwm_r)
                    _pwm_dirty = False
                else:
                    _mouse.poll()
            except Exception:
                pass
        time.sleep(step_ms / 1000.0)
        
    # Sleep any remaining fractional time
    rem_ms = ms % step_ms
    if rem_ms > 0:
        time.sleep(rem_ms / 1000.0)

def set_polarity(left_polarity, right_polarity):
    """Sets motor polarity multipliers on the physical mouse (ignored on PC)."""
    pass