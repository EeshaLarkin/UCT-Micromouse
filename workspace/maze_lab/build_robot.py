#!/usr/bin/env python3
# =========================================================================
# build_robot.py  -  Make compact copies of the solver and upload them
# =========================================================================
# Run from the repo root (C:\Users\eesha\UCT-Micromouse):
#
#   python workspace/maze_lab/build_robot.py                    # build only
#   python workspace/maze_lab/build_robot.py --port COM5        # build + upload
#   python workspace/maze_lab/build_robot.py --port auto        # let mpremote find it
#   python workspace/maze_lab/build_robot.py --port COM5 --main-as mission.py
#        -> uploads main.py as mission.py so it does NOT run at power-on
#   python workspace/maze_lab/build_robot.py --port COM5 --extra workspace/maze_lab/calibrate.py
#   python workspace/maze_lab/build_robot.py --port COM5 --mpy  # precompiled .mpy (needs mpy-cross)
#
# What it does
#   1. Parses each module with Python's ast, removes docstrings, and writes it
#      back with ast.unparse (which also drops every comment) into
#      workspace/maze_lab/build_robot/. Your source files are never changed.
#   2. Warns if the total is over ~50 KB (the /flash drive is 64 KB, shared
#      with boot.py and anything else you keep on it).
#   3. With --port, uploads each file with
#          python -m mpremote connect <port> resume fs cp <file> :<file>
#      'resume' skips mpremote's soft reset, which this firmware doesn't
#      survive ("could not enter raw repl").
#
# Afterwards (the RESET button isn't needed):
#   - run it over USB:     python -m mpremote connect COM5 resume exec "import mission"
#   - or on battery:       unplug USB, switch the battery OFF then ON -> main.py runs
#   - REPL:                python -m mpremote connect COM5 resume repl
#
# Stripping saves FLASH. If importing on the mouse runs out of RAM
# (MemoryError), use --mpy: the mouse then loads ready-made bytecode
# instead of compiling the source itself.
# =========================================================================

import argparse
import ast
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO, "workspace", "final_task")
BUILD = os.path.join(HERE, "build_robot")
DEFAULT_MODULES = ["maze_logic.py", "motion.py", "main.py"]
FLASH_WARN_BYTES = 50 * 1024


def strip_docstrings(tree):
    """Remove the docstring (a bare string as the first statement) from the
    module, every class and every function. An emptied body gets 'pass'."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body.pop(0)
                if not body:
                    body.append(ast.Pass())
    return tree


def compact(src_path):
    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=src_path)
    code = ast.unparse(strip_docstrings(tree)) + "\n"
    compile(code, src_path, "exec")          # sanity check: still valid Python
    return source, code


def find_mpy_cross():
    exe = shutil.which("mpy-cross")
    if exe:
        return [exe]
    try:
        import mpy_cross  # noqa: F401  (pip install mpy-cross)
        return [sys.executable, "-m", "mpy_cross"]
    except ImportError:
        return None


def upload(port, local, remote):
    cmd = [sys.executable, "-m", "mpremote"]
    if port and port != "auto":
        cmd += ["connect", port]
    cmd += ["resume", "fs", "cp", local, ":" + remote]
    print("  $", " ".join(cmd))
    return subprocess.call(cmd) == 0


def main():
    p = argparse.ArgumentParser(description="Build compact robot copies and upload them")
    p.add_argument("--port", help="COM port (e.g. COM5) or 'auto'; omit to build only")
    p.add_argument("--main-as", default="main.py",
                   help="name to give main.py on the robot (e.g. mission.py)")
    p.add_argument("--extra", nargs="*", default=[],
                   help="more .py files to include (e.g. workspace/maze_lab/calibrate.py)")
    p.add_argument("--mpy", action="store_true",
                   help="also precompile with mpy-cross and upload .mpy (main stays .py)")
    a = p.parse_args()

    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    sources = [os.path.join(SRC, m) for m in DEFAULT_MODULES] + [os.path.abspath(e) for e in a.extra]
    built = []                                   # (local_path, remote_name)
    total_src = total_out = 0
    print("Building compact copies into", BUILD)
    for path in sources:
        name = os.path.basename(path)
        remote = a.main_as if name == "main.py" else name
        try:
            source, code = compact(path)
        except (OSError, SyntaxError) as e:
            print("!! %s: %s" % (name, e))
            sys.exit(1)
        out = os.path.join(BUILD, remote)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        n_src = len(source.encode())
        n_out = len(code.encode())
        total_src += n_src
        total_out += n_out
        print("  %-16s %6d -> %6d bytes" % (remote, n_src, n_out))
        built.append((out, remote))

    if a.mpy:
        mc = find_mpy_cross()
        if not mc:
            print("!! mpy-cross not found: pip install mpy-cross")
            sys.exit(1)
        converted = []
        for out, remote in built:
            if remote == "main.py":              # boot.py runs main.py by name
                converted.append((out, remote))
                continue
            mpy_out = out[:-3] + ".mpy"
            if subprocess.call(mc + ["-o", mpy_out, out]) != 0:
                print("!! mpy-cross failed on", remote)
                sys.exit(1)
            print("  %-16s -> %s (%d bytes)" % (remote, os.path.basename(mpy_out),
                                                os.path.getsize(mpy_out)))
            converted.append((mpy_out, remote[:-3] + ".mpy"))
        built = converted
        total_out = sum(os.path.getsize(f) for f, _ in built)

    print("Total %d -> %d bytes (%.1f KB)" % (total_src, total_out, total_out / 1024.0))
    if total_out > FLASH_WARN_BYTES:
        print("!! Over ~50 KB: the 64 KB /flash drive may run out of space")

    if not a.port:
        print("Built only (add --port COMx to upload).")
        return

    print("Uploading...")
    for local, remote in built:
        if not upload(a.port, local, remote):
            print("!! Upload of %s failed - check the port, close other mpremote windows" % remote)
            sys.exit(1)
    if a.mpy:
        print("NOTE: delete any old .py copies of these modules on the drive -")
        print("      MicroPython prefers a .py over a .mpy with the same name.")
    print("Done.")
    if a.main_as == "main.py":
        print("main.py will run at the next power-on (battery OFF->ON with USB unplugged).")
    else:
        print('Start it over USB: python -m mpremote connect %s resume exec "import %s"'
              % (a.port if a.port != "auto" else "auto", a.main_as[:-3]))


if __name__ == "__main__":
    main()
