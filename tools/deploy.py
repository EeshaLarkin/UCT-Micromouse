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
        "--script", "-s",
        default=None,
        help="Path to the student python entry script to deploy (default: python/main.py or search for other files)"
    )
    args = parser.parse_args()

    print("=== UCT Micromouse Firmware Deployer ===")
    print(f"Selected engine: {args.engine.upper()}")
    
    # Dynamically resolve paths so the script can be run from anywhere
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))

    # Resolve target script path
    if args.script:
        target_script = os.path.abspath(args.script)
    else:
        # Default to main.py
        target_script = os.path.join(repo_root, "python", "main.py")
        
    if args.engine in ["pikascript", "micropython"]:
        if not os.path.exists(target_script):
            print(f"Error: Target Python script not found at {target_script}")
            print("Please specify the script using --script <path> (e.g. --script python/milestone1.py)")
            sys.exit(1)
        print(f"Target script: {target_script}")

    if args.engine == "pikascript":
        # === PIKASCRIPT ENGINE FLOW ===
        print(f"[1/3] Bundling {os.path.basename(target_script)} and compiling firmware...")
        
        # Copy the student's code so the Rust compiler sees it as the entry point
        shutil.copy(target_script, os.path.join(repo_root, "src", "pikascript", "main.py"))
        
        print("    -> Running PikaScript Pre-compiler...")
        pika_dir = os.path.join(repo_root, "src", "pikascript")
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
        print(f"    -> Embedding {os.path.basename(target_script)} into C-Kernel...")
        header_path = os.path.join(repo_root, "src", "kernel", "inc", "student_code.h")
        with open(target_script, "r") as f_py, open(header_path, "w") as f_h:
            f_h.write("#ifndef STUDENT_CODE_H\n#define STUDENT_CODE_H\n")
            f_h.write('const char* student_python_code = \n')
            for line in f_py:
                escaped = line.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                f_h.write(f'"{escaped}"\n')
            f_h.write(";\n#endif\n")
            
        try:
            print("    -> Configuring CMake...")
            subprocess.run(["cmake", "-B", "build"], cwd=repo_root, check=True)
            print("    -> Building PikaScript firmware target...")
            subprocess.run(["cmake", "--build", "build", "--target", "pikascript_firmware"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            print("Build failed! Check your C-Kernel and PikaScript bindings.")
            sys.exit(1)
        
        bin_path = os.path.join(repo_root, "build", "pikascript_firmware.bin")
        central_bin_path = os.path.join(repo_root, "firmware", "pikascript.bin")
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
        simulink_dir = os.path.join(repo_root, "build", "UCT_KDeploy_ert_rtw")
        if not os.path.exists(simulink_dir):
            print(f"Warning: Simulink code-gen directory not found at {simulink_dir}.")
            print("Please run Code Generation (Ctrl+B) in your Simulink model before compiling!")
            
        try:
            print("    -> Configuring CMake...")
            subprocess.run(["cmake", "-B", "build"], cwd=repo_root, check=True)
            print("    -> Building Simulink firmware target...")
            subprocess.run(["cmake", "--build", "build", "--target", "simulink_firmware"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            print("Build failed! Check your Simulink autocoded source files.")
            sys.exit(1)
            
        # Copy to central firmware/ directory
        bin_path = os.path.join(repo_root, "build", "simulink_firmware.bin")
        central_bin_path = os.path.join(repo_root, "firmware", "simulink.bin")
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
                if not os.path.exists(symlink_path):
                    # Create symlink: boards/UCT_MICROMOUSE -> ../../../../../src/micropython/boards/UCT_MICROMOUSE
                    os.symlink("../../../../../src/micropython/boards/UCT_MICROMOUSE", symlink_path)
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
            central_bin_path = os.path.join(repo_root, "firmware", "micropython.bin")
            shutil.copy(mpy_bin_path, central_bin_path)
            print(f"    -> Copied compiled firmware to {central_bin_path}")
            
            # Find the ST-Link Mass Storage Drive
            drive = find_stlink_drive()
            if not drive:
                print("Error: Could not find ST-Link USB drive. Is the board plugged in?")
                sys.exit(1)
                
            # Flash by copying to the Mass Storage Drive
            print(f"[2/2] ST-Link found at {drive}. Flashing MicroPython firmware...")
            if sys.platform == 'darwin':
                dest_path = os.path.join(drive, "firmware.bin")
                with open(central_bin_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                    f_dst.write(f_src.read())
            else:
                shutil.copy(central_bin_path, drive)
            print("Success! MicroPython interpreter is flashed. The board will reboot and mount as a USB drive shortly.")
            
        else:
            # --- Deploying Python Scripts to the Virtual USB Drive ---
            print("[1/2] Finding MicroPython virtual USB drive...")
            mpy_drive = find_micropython_drive()
            if not mpy_drive:
                print("Error: MicroPython virtual USB drive not found!")
                print("Hints:")
                print("  1. Make sure the board is flashed with MicroPython (run this script with -f/--flash first).")
                print("  2. Check if the USB cable is connected to the USB OTG port, not just the ST-Link port.")
                print("  3. Make sure the board is powered on and mounted on your system.")
                sys.exit(1)
                
            print(f"Found MicroPython drive at: {mpy_drive}")
            print(f"[2/2] Deploying {os.path.basename(target_script)} to the mouse...")
            
            # Copy the target script as main.py
            dest_main_path = os.path.join(mpy_drive, "main.py")
            print(f"    -> Copying {os.path.basename(target_script)} as main.py to board...")
            if sys.platform == 'darwin':
                with open(target_script, "rb") as f_src, open(dest_main_path, "wb") as f_dst:
                    f_dst.write(f_src.read())
            else:
                shutil.copy(target_script, dest_main_path)
            deployed_count = 1
            
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
                if item in ["uct_mouse.py", "micromouse.py"]:
                    continue
                # Skip other milestone/main files to avoid clutter
                if item.startswith("milestone") or item == "main.py":
                    continue
                
                dest_file_path = os.path.join(mpy_drive, item)
                print(f"    -> Copying helper {item} to board...")
                if sys.platform == 'darwin':
                    with open(item_path, "rb") as f_src, open(dest_file_path, "wb") as f_dst:
                        f_dst.write(f_src.read())
                else:
                    shutil.copy(item_path, mpy_drive)
                deployed_count += 1
                
            print(f"Success! {deployed_count} python scripts copied to MicroPython drive. Eject the drive or reset the board to run.")