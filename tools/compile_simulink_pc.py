#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import shutil

def main():
    print("=== Standalone Simulink PC Client Compiler ===")
    
    # 1. Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    simulink_dir = os.path.join(root_dir, "matlab", "simulink")
    src_kernel_dir = os.path.join(root_dir, "src", "kernel")
    
    # 2. Find code generation directory
    ert_dirs = []
    build_dir = os.path.join(root_dir, "build")
    
    # Check build_dir
    if os.path.exists(build_dir):
        for d in os.listdir(build_dir):
            path = os.path.join(build_dir, d)
            if d.endswith("_ert_rtw") and os.path.isdir(path):
                ert_dirs.append((path, d))
                
    # Check simulink_dir
    if os.path.exists(simulink_dir):
        for d in os.listdir(simulink_dir):
            path = os.path.join(simulink_dir, d)
            if d.endswith("_ert_rtw") and os.path.isdir(path):
                ert_dirs.append((path, d))
                
    # Check root_dir
    for d in os.listdir(root_dir):
        path = os.path.join(root_dir, d)
        if d.endswith("_ert_rtw") and os.path.isdir(path):
            ert_dirs.append((path, d))
            
    if not ert_dirs:
        print("[Error] No Simulink code generation folder (*_ert_rtw) found in 'simulink/' or root directory.")
        print("Please generate C code from your Simulink model first (e.g. UCT_KDeploy.slx):")
        print(" 1. Open your Simulink model in MATLAB.")
        print(" 2. Configure Code Generation to use Embedded Real-Time target (ert.tlc).")
        print(" 3. Build the model (Ctrl+B).")
        sys.exit(1)
        
    # Pick the first one or UCT_KDeploy_ert_rtw if available
    target_path, target_name = None, None
    for path, name in ert_dirs:
        if name == "UCT_KDeploy_ert_rtw":
            target_path, target_name = path, name
            break
            
    if not target_path:
        target_path, target_name = ert_dirs[0]
        
    model_name = target_name[:-8] # Remove "_ert_rtw"
    model_dir_path = target_path
    print(f"[Info] Found code generation directory: {target_path}")
    print(f"[Info] Model Name detected: {model_name}")
    
    # 3. Locate all source files to compile
    # We compile PC_client_main.c, simulink_wrapper.c, and all C files in model_dir except ert_main.c
    pc_main = os.path.join(simulink_dir, "PC_client_main.c")
    sim_wrapper = os.path.join(src_kernel_dir, "src", "simulink_wrapper.c")
    
    if not os.path.exists(pc_main):
        print(f"[Error] Required main file not found: {pc_main}")
        sys.exit(1)
    if not os.path.exists(sim_wrapper):
        print(f"[Error] Required wrapper file not found: {sim_wrapper}")
        sys.exit(1)
        
    model_sources = glob.glob(os.path.join(model_dir_path, "*.c"))
    # Exclude ert_main.c
    model_sources = [f for f in model_sources if os.path.basename(f) != "ert_main.c"]
    
    all_sources = [pc_main, sim_wrapper] + model_sources
    
    # 4. Formulate compiler paths and options
    include_dirs = [
        model_dir_path,
        os.path.join(src_kernel_dir, "inc")
    ]
    
    # 5. Detect and choose compiler
    is_windows = sys.platform.startswith("win")
    compiler = None
    
    if is_windows:
        # Check for MSVC cl.exe
        if shutil.which("cl"):
            compiler = "msvc"
        elif shutil.which("gcc"):
            compiler = "gcc"
        elif shutil.which("clang"):
            compiler = "clang"
    else:
        if shutil.which("clang"):
            compiler = "clang"
        elif shutil.which("gcc"):
            compiler = "gcc"
            
    if not compiler:
        print("[Error] No suitable C compiler found (clang, gcc, or cl.exe).")
        print("Please install GCC/Clang or Visual Studio Build Tools, and ensure it is in your PATH.")
        sys.exit(1)
        
    print(f"[Info] Using compiler: {compiler}")
    
    # Build Output Name
    output_bin = "simulink_client"
    if is_windows:
        output_bin += ".exe"
    output_path = os.path.join(simulink_dir, output_bin)
    
    # 6. Build compilation command
    cmd = []
    if compiler == "msvc":
        cmd = ["cl", "/EHsc", f"/DMODEL_NAME={model_name}"]
        for d in include_dirs:
            cmd.append(f"/I{d}")
        cmd.extend(all_sources)
        cmd.append("ws2_32.lib")
        cmd.append(f"/Fe{output_path}")
    else:
        # gcc or clang
        cmd = [compiler, "-O2", f"-DMODEL_NAME={model_name}"]
        for d in include_dirs:
            cmd.append(f"-I{d}")
        cmd.extend(all_sources)
        if is_windows:
            cmd.append("-lws2_32")
        cmd.extend(["-o", output_path])
        
    print(f"[Info] Executing compile command:")
    print(" ".join(cmd))
    
    # 7. Run compilation
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"\n[Success] STANDALONE CLIENT BUILT SUCCESSFULLY!")
            print(f"Executable is located at: {output_path}")
            print(f"You can now run this standalone binary to control the tools/physics_sim.py on port 8000.")
        else:
            print(f"\n[Error] Compilation failed with return code {res.returncode}")
            print("--- STDOUT ---")
            print(res.stdout)
            print("--- STDERR ---")
            print(res.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[Error] Failed to invoke compiler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
