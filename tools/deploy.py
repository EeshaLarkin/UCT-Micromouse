import os
import sys
import shutil
import subprocess
import glob
import argparse

def find_stlink_drive():
    """Finds the ST-Link mass storage drive on Mac/Windows/Linux."""
    if sys.platform == 'darwin':
        drives = glob.glob('/Volumes/NOD*') + glob.glob('/Volumes/*STLINK*')
    elif sys.platform == 'win32':
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                # Rough heuristic for Windows; ideally check volume label
                if os.path.exists(f"{letter}:\\DETAILS.TXT"):
                    drives.append(f"{letter}:\\")
            bitmask >>= 1
    else:
        drives = glob.glob('/media/*/NOD*') + glob.glob('/run/media/*/NOD*')
        
    return drives[0] if drives else None

def find_micropython_drive():
    """Finds the MicroPython virtual USB drive on Mac/Windows/Linux."""
    if sys.platform == 'darwin':
        drives = (
            glob.glob('/Volumes/UCT-MICROMO*') +
            glob.glob('/Volumes/UCT_MICROMO*') +
            glob.glob('/Volumes/UCT-MICROMOUSE*') +
            glob.glob('/Volumes/PYB*')
        )
    elif sys.platform == 'win32':
        import string
        import ctypes
        drives = []
        kernel32 = ctypes.windll.kernel32
        volumeNameBuffer = ctypes.create_unicode_buffer(1024)
        bitmask = kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                res = kernel32.GetVolumeInformationW(
                    drive_path, volumeNameBuffer, ctypes.sizeof(volumeNameBuffer),
                    None, None, None, None, 0
                )
                if res:
                    label = volumeNameBuffer.value.upper()
                    if "UCT-MICRO" in label or "UCT_MICRO" in label or "PYB" in label:
                        drives.append(drive_path)
            bitmask >>= 1
    else:
        drives = (
            glob.glob('/media/*/*UCT-MICROMO*') +
            glob.glob('/run/media/*/*UCT-MICROMO*') +
            glob.glob('/media/*/*UCT_MICROMO*') +
            glob.glob('/run/media/*/*UCT_MICROMO*') +
            glob.glob('/media/*/*PYB*') +
            glob.glob('/run/media/*/*PYB*')
        )
    return drives[0] if drives else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCT Micromouse Firmware and Script Deployer")
    parser.add_argument(
        "--engine", "-e",
        choices=["pikascript", "micropython", "simulink"],
        default="pikascript",
        help="Select the firmware engine to deploy (default: pikascript)"
    )
    parser.add_argument(
        "--flash", "-f",
        action="store_true",
        help="Flash the engine's compiled C firmware binary onto the board using the ST-Link drive (always happens for pikascript and simulink)."
    )
    parser.add_argument(
        "--script-only", "-o",
        action="store_true",
        help="Directly write the Python script to the STM32 flash page at 0x08078000 using st-flash. Bypasses firmware compilation and runs in <100ms. (Only for PikaScript)."
    )
    parser.add_argument(
        "--script", "-s",
        default=None,
        help="Path to a specific python script to deploy as main.py. If omitted, mirrors the entire --src-dir."
    )
    parser.add_argument(
        "--src-dir", "-d",
        default="python/src",
        help="Path to the dedicated python development folder to mirror to the mouse (default: python/src)"
    )
    parser.add_argument(
        "--port", "-p",
        default=None,
        help="Specify the serial port to use for deployment (overrides auto-detection)."
    )
    args = parser.parse_args()

    print("=== UCT Micromouse Firmware Deployer ===")
    print(f"Selected engine: {args.engine.upper()}")
    
    # Dynamically resolve paths so the script can be run from anywhere
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))

    # Resolve target paths
    target_script = None
    target_dir = None
    
    if args.script:
        target_script = os.path.abspath(args.script)
    else:
        target_dir = os.path.abspath(args.src_dir)
        
    if args.engine in ["pikascript", "micropython"]:
        if target_script and not os.path.exists(target_script):
            print(f"Error: Target Python script not found at {target_script}")
            sys.exit(1)
        elif not target_script and not os.path.exists(target_dir):
            print(f"Error: Target Python directory not found at {target_dir}")
            sys.exit(1)

    if args.engine == "pikascript":
        # PikaScript requires a single main.py entry point
        pika_target = target_script if target_script else os.path.join(target_dir, "main.py")
        if not os.path.exists(pika_target):
            print(f"Error: PikaScript requires a single entry point script. Could not find {pika_target}")
            sys.exit(1)
            
        if args.script_only:
            # === SCRIPT ONLY MODE ===
            print(f"=== Script-Only Flash Mode ===")
            print(f"Target script: {os.path.basename(pika_target)}")
            
            with open(pika_target, "rb") as f_in:
                py_content = f_in.read() + b"\x00"
                
            temp_bin = os.path.join(repo_root, "build", "script_only.bin")
            os.makedirs(os.path.dirname(temp_bin), exist_ok=True)
            with open(temp_bin, "wb") as f_out:
                f_out.write(py_content)
                
            print("Flashing Python script directly to 0x08078000 (Page 240)...")
            try:
                st_flash_cmd = "st-flash"
                if os.path.exists("/opt/local/bin/st-flash"):
                    st_flash_cmd = "/opt/local/bin/st-flash"
                elif os.path.exists("/usr/local/bin/st-flash"):
                    st_flash_cmd = "/usr/local/bin/st-flash"
                    
                subprocess.run([st_flash_cmd, "--reset", "write", temp_bin, "0x08078000"], check=True)
                print("Success! Script flashed in <100ms. Board reset triggered.")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print("Error: Direct flashing failed! Please ensure 'st-flash' is installed on your PATH.")
                print(f"Details: {e}")
                sys.exit(1)
            sys.exit(0)
            
        # === PIKASCRIPT ENGINE FLOW ===
        print(f"[1/3] Bundling {os.path.basename(pika_target)} and compiling firmware...")
        
        # Copy user script to PikaScript directory and precompile
        shutil.copy(pika_target, os.path.join(repo_root, "firmware", "src", "pikascript", "main.py"))
        
        print("    -> Running PikaScript Pre-compiler...")
        pika_dir = os.path.join(repo_root, "firmware", "src", "pikascript")
        tools_dir = os.path.join(repo_root, "tools")
        if sys.platform == 'darwin':
            precompiler = os.path.join(tools_dir, "rust-msc-mac")
        elif sys.platform == 'win32':
            precompiler = os.path.join(tools_dir, "rust-msc-win10.exe")
        else:
            precompiler = os.path.join(tools_dir, "rust-msc-linux")
            
        try:
            subprocess.run([precompiler], cwd=pika_dir, check=True)
        except FileNotFoundError:
            print(f"Error: Could not find PikaScript pre-compiler '{precompiler}' in {pika_dir}")
            sys.exit(1)
            
        # Convert the target script into a C-string header to guarantee it gets compiled into the binary
        print(f"    -> Embedding {os.path.basename(pika_target)} into C-Kernel...")
        header_path = os.path.join(repo_root, "firmware", "src", "kernel", "inc", "student_code.h")
        with open(pika_target, "r") as f_py, open(header_path, "w") as f_h:
            f_h.write("#ifndef STUDENT_CODE_H\n#define STUDENT_CODE_H\n")
            f_h.write('const char* student_python_code = \n')
            for line in f_py:
                escaped = line.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                f_h.write(f'"{escaped}"\n')
            f_h.write(";\n#endif\n")
            
        try:
            print("    -> Configuring CMake...")
            subprocess.run(["cmake", "-S", "firmware", "-B", "firmware/build"], cwd=repo_root, check=True)
            print("    -> Building PikaScript firmware target...")
            subprocess.run(["cmake", "--build", "firmware/build", "--target", "pikascript_firmware"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            print("Build failed! Check your C-Kernel and PikaScript bindings.")
            sys.exit(1)
        
        bin_path = os.path.join(repo_root, "firmware", "build", "pikascript_firmware.bin")
        central_bin_path = os.path.join(repo_root, "firmware", "binaries", "pikascript.bin")
        if not os.path.exists(bin_path):
            print(f"Error: Compiled firmware not found at {bin_path}")
            sys.exit(1)
        shutil.copy(bin_path, central_bin_path)
        print(f"    -> Copied compiled firmware to {central_bin_path}")
            
        # Find the ST-Link Mass Storage Drive
        drive = find_stlink_drive()
        if not drive:
            print("Error: Could not find ST-Link USB drive. Is the board plugged in?")
            sys.exit(1)
            
        # Flash by copying to the Mass Storage Drive
        print(f"[2/3] ST-Link found at {drive}. Flashing PikaScript firmware...")
        if sys.platform == 'darwin':
            dest_path = os.path.join(drive, "firmware.bin")
            with open(central_bin_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                f_dst.write(f_src.read())
        else:
            shutil.copy(central_bin_path, drive)
        print("[3/3] Success! Mouse will automatically reboot and run main.py.")

    elif args.engine == "simulink":
        # === SIMULINK ENGINE FLOW ===
        print("[1/2] Compiling Simulink firmware...")
        
        # Check if code generation outputs are present
        simulink_dir = os.path.join(repo_root, "firmware", "build", "UCT_KDeploy_ert_rtw")
        if not os.path.exists(simulink_dir):
            print(f"Warning: Simulink code-gen directory not found at {simulink_dir}.")
            print("Please run Code Generation (Ctrl+B) in your Simulink model before compiling!")
            
        try:
            print("    -> Configuring CMake...")
            subprocess.run(["cmake", "-S", "firmware", "-B", "firmware/build"], cwd=repo_root, check=True)
            print("    -> Building Simulink firmware target...")
            subprocess.run(["cmake", "--build", "firmware/build", "--target", "simulink_firmware"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            print("Build failed! Check your Simulink autocoded source files.")
            sys.exit(1)
            
        # Copy to central firmware/ directory
        bin_path = os.path.join(repo_root, "firmware", "build", "simulink_firmware.bin")
        central_bin_path = os.path.join(repo_root, "firmware", "binaries", "simulink.bin")
        if not os.path.exists(bin_path):
            print(f"Error: Compiled firmware not found at {bin_path}")
            sys.exit(1)
        shutil.copy(bin_path, central_bin_path)
        print(f"    -> Copied compiled firmware to {central_bin_path}")
        
        # Find the ST-Link Mass Storage Drive
        drive = find_stlink_drive()
        if not drive:
            print("Error: Could not find ST-Link USB drive. Is the board plugged in?")
            sys.exit(1)
            
        # Flash by copying to the Mass Storage Drive
        print(f"[2/2] ST-Link found at {drive}. Flashing Simulink firmware...")
        if sys.platform == 'darwin':
            dest_path = os.path.join(drive, "firmware.bin")
            with open(central_bin_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                f_dst.write(f_src.read())
        else:
            shutil.copy(central_bin_path, drive)
        print("Success! Simulink firmware is flashed. The board will automatically reboot and execute.")

    else:
        # === MICROPYTHON ENGINE FLOW ===
        if args.flash:
            # --- Flashing the MicroPython C-Firmware ---
            print("[1/2] Preparing MicroPython firmware binary...")
            mpy_bin_path = os.path.join(
                repo_root, "external", "micropython", "ports", "stm32", 
                "build-UCT_MICROMOUSE", "firmware.bin"
            )
            
            # Compile the firmware to incorporate any changes
            print("    -> Compiling MicroPython firmware...")
            mpy_ports_dir = os.path.join(repo_root, "external", "micropython", "ports", "stm32")
            symlink_path = os.path.join(mpy_ports_dir, "boards", "UCT_MICROMOUSE")
            
            created_symlink = False
            try:
                if not os.path.lexists(symlink_path):
                    # Create symlink: boards/UCT_MICROMOUSE -> ../../../../../firmware/src/micropython/boards/UCT_MICROMOUSE
                    os.symlink("../../../../../firmware/src/micropython/boards/UCT_MICROMOUSE", symlink_path)
                    created_symlink = True
                
                subprocess.run(["make", "BOARD=UCT_MICROMOUSE"], cwd=mpy_ports_dir, check=True)
            except Exception as e:
                print(f"Build failed: {e}")
                sys.exit(1)
            finally:
                if created_symlink and os.path.exists(symlink_path):
                    try:
                        os.remove(symlink_path)
                    except Exception:
                        pass
                        
            if not os.path.exists(mpy_bin_path):
                print(f"Error: Compiled firmware not found at {mpy_bin_path}")
                sys.exit(1)
                
            # Copy to central firmware/ directory
            central_bin_path = os.path.join(repo_root, "firmware", "binaries", "micropython.bin")
            shutil.copy(mpy_bin_path, central_bin_path)
            print(f"    -> Copied compiled firmware to {central_bin_path}")
            
            # Try to use st-flash for high stability (resolves macOS USB ghosting/lockup issues)
            st_flash_cmd = None
            for p in ["/opt/local/bin/st-flash", "/usr/local/bin/st-flash", "st-flash"]:
                if os.path.exists(p) or shutil.which(p):
                    st_flash_cmd = p
                    break
            
            flashed_via_st_flash = False
            if st_flash_cmd:
                print(f"[2/2] ST-Link tool found at {st_flash_cmd}. Flashing MicroPython firmware...")
                try:
                    subprocess.run([st_flash_cmd, "--reset", "write", central_bin_path, "0x08000000"], check=True)
                    print("Success! MicroPython interpreter is flashed and board is rebooted.")
                    flashed_via_st_flash = True
                    # Brief delay for USB port enumeration
                    import time
                    time.sleep(2.0)
                except Exception as e:
                    print(f"    -> st-flash failed ({e}), falling back to USB drive copy...")
            
            if not flashed_via_st_flash:
                # Find the ST-Link Mass Storage Drive
                drive = find_stlink_drive()
                if not drive:
                    print("Error: Could not find ST-Link USB drive. Is the board plugged in?")
                    sys.exit(1)
                    
                # Flash by copying to the Mass Storage Drive
                print(f"[2/2] ST-Link drive found at {drive}. Flashing MicroPython firmware...")
                if sys.platform == 'darwin':
                    dest_path = os.path.join(drive, "firmware.bin")
                    with open(central_bin_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                        f_dst.write(f_src.read())
                else:
                    shutil.copy(central_bin_path, drive)
                print("Success! MicroPython interpreter is flashed. The board will reboot and mount as a USB drive shortly.")
            
        else:
            # --- Deploying Python Scripts via VCP (mpremote) ---
            print("[1/2] Connecting to MicroPython via Serial (mpremote)...")
            
            # Dynamically detect MicroPython port to avoid ST-Link VCP conflicts
            mpy_port = args.port
            if not mpy_port:
                try:
                    import serial.tools.list_ports
                    for p in serial.tools.list_ports.comports():
                        if p.vid == 0xf055 and p.pid in (0x9800, 0x9802):
                            mpy_port = p.device
                            break
                except Exception:
                    pass
                
            mpremote_cmd = [sys.executable, "-m", "mpremote"]
            if mpy_port:
                print(f"    -> Using MicroPython port: {mpy_port}")
                # Cleanse port (send CTRL-C and flush) to stop any running script and clear boot logs
                try:
                    import serial
                    import time
                    s = serial.Serial(mpy_port, 115200, timeout=0.5)
                    s.write(b'\x03')
                    time.sleep(0.1)
                    s.write(b'\x03')
                    time.sleep(0.1)
                    s.reset_input_buffer()
                    s.close()
                except Exception:
                    pass
                mpremote_cmd += ["connect", mpy_port]
            try:
                subprocess.run(mpremote_cmd + ["exec", "print('Connected!')"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print("Error: Could not connect to MicroPython board via serial!")
                print("Hints:")
                print("  1. Make sure the board is flashed with MicroPython (run this script with -f/--flash first).")
                print("  2. Check if the USB cable is connected to the main USB OTG port.")
                print("  3. Make sure the board is powered on.")
                sys.exit(1)
            except FileNotFoundError:
                print("Error: 'mpremote' command/module not found. Please run 'pip install mpremote' or 'pip install -r python/requirements.txt'")
                sys.exit(1)
                
            if target_script:
                print(f"[2/2] Deploying {os.path.basename(target_script)} and bootloader to the mouse...")
                
                # Copy boot.py (Hybrid Bootloader)
                boot_script = os.path.join(repo_root, "python", "boot.py")
                if os.path.exists(boot_script):
                    print("    -> Pushing boot.py (Hybrid Read-Only/Read-Write logic)...")
                    subprocess.run(mpremote_cmd + ["fs", "cp", boot_script, ":boot.py"], check=True)
                
                # Copy the target script as main.py
                print(f"    -> Pushing {os.path.basename(target_script)} as main.py...")
                subprocess.run(mpremote_cmd + ["fs", "cp", target_script, ":main.py"], check=True)
                deployed_count = 1
                if os.path.exists(boot_script):
                    deployed_count += 1
                
                # Copy other helper python files from the same directory
                script_dir_path = os.path.dirname(target_script)
                for item in os.listdir(script_dir_path):
                    item_path = os.path.join(script_dir_path, item)
                    if os.path.isdir(item_path) or not item.endswith(".py"):
                        continue
                    # Skip the target script itself (already copied as main.py)
                    if item == os.path.basename(target_script):
                        continue
                    # Skip standard PC-only mock libraries and known milestone scripts
                    if item in ["uct_mouse.py", "micromouse.py", "boot.py"]:
                        continue
                    # Skip other milestone/main files to avoid clutter
                    if item.startswith("milestone") or item == "main.py":
                        continue
                    
                    print(f"    -> Pushing helper {item}...")
                    subprocess.run(mpremote_cmd + ["fs", "cp", item_path, f":{item}"], check=True)
                    deployed_count += 1
            else:
                print(f"[2/2] Mirroring {os.path.basename(target_dir)}/ development folder to the mouse...")
                
                # Push boot.py to the root first
                boot_script = os.path.join(repo_root, "python", "boot.py")
                if os.path.exists(boot_script):
                    print("    -> Pushing boot.py (Hybrid Read-Only/Read-Write logic)...")
                    subprocess.run(mpremote_cmd + ["fs", "cp", boot_script, ":boot.py"], check=True)
                
                # Copy all contents of target_dir directly to the flash root
                print(f"    -> Syncing directory contents from {target_dir} to root ...")
                for item in os.listdir(target_dir):
                    item_path = os.path.join(target_dir, item)
                    # Skip hidden files
                    if item.startswith('.'):
                        continue
                    print(f"    -> Pushing {item}...")
                    subprocess.run(mpremote_cmd + ["fs", "cp", "-r", item_path, f":{item}"], check=True)
                deployed_count = "all"
                
            print(f"Success! {deployed_count} python scripts copied via serial to internal flash.")
            print("Soft-rebooting the board...")
            subprocess.run(mpremote_cmd + ["soft-reset"], check=False)
            print("Done! The mouse is now running your code.")