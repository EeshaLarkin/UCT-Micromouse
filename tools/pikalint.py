#!/usr/bin/env python3
import ast
import warnings as py_warnings
py_warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os

# Terminal color formatting helper
def print_colored(text, color):
    colors = {
        "red": "\033[91m",
        "yellow": "\033[93m",
        "green": "\033[92m",
        "blue": "\033[94m",
        "bold": "\033[1m",
        "end": "\033[0m"
    }
    # Check if stdout is a tty (supports colors)
    if sys.stdout.isatty():
        return f"{colors.get(color, '')}{text}{colors.get('end', '')}"
    return text

class PikaLintVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.loop_depth = 0

    def add_error(self, node, msg):
        self.errors.append((node.lineno, msg))

    def add_warning(self, node, msg):
        self.warnings.append((node.lineno, msg))

    def visit_If(self, node):
        # Check inline statement: body starts on the same line as the 'if' condition
        if node.body and node.body[0].lineno == node.lineno:
            self.add_error(node, "Inline conditional body detected ('if cond: stmt'). PikaScript requires the body to be indented on a new line.")
        self.generic_visit(node)

    def visit_While(self, node):
        # Check inline loop
        if node.body and node.body[0].lineno == node.lineno:
            self.add_error(node, "Inline while loop body detected ('while cond: stmt'). PikaScript requires the loop body to be indented on a new line.")
        
        self.loop_depth += 1
        if self.loop_depth > 1:
            self.add_warning(node, f"Nested loop detected (depth: {self.loop_depth}). PikaScript bytecode jumps can get corrupted in nested loops. Try to restructure your code to keep loops flat.")
        
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_For(self, node):
        # Check inline loop
        if node.body and node.body[0].lineno == node.lineno:
            self.add_error(node, "Inline for loop body detected ('for var in seq: stmt'). PikaScript requires the loop body to be indented on a new line.")
        
        self.loop_depth += 1
        if self.loop_depth > 1:
            self.add_warning(node, f"Nested loop detected (depth: {self.loop_depth}). PikaScript bytecode jumps can get corrupted in nested loops. Try to restructure your code to keep loops flat.")
        
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_Call(self, node):
        # Check for file system calls
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ('open', 'file'):
                self.add_error(node, f"Dangerous built-in function '{func_name}()' detected. Microcontrollers run bare-metal; calling file I/O triggers Semihosting (ARM BKPT 0xAB) which freezes the microcontroller instantly.")
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if func_name in ('read', 'write', 'open') and isinstance(node.func.value, ast.Name) and node.func.value.id not in ('uct_mouse', 'mouse'):
                self.add_error(node, f"Dangerous file system attribute access '.{func_name}()' detected. Reading or writing files will freeze the microcontroller.")
        self.generic_visit(node)

    def visit_BinOp(self, node):
        # Check for mixed type math literals (int and float)
        def get_literal_type(subnode):
            if isinstance(subnode, ast.Constant):  # Python 3.8+
                return type(subnode.value)
            elif isinstance(subnode, ast.Num):  # Legacy Python
                return type(subnode.n)
            return None

        type_l = get_literal_type(node.left)
        type_r = get_literal_type(node.right)

        if type_l and type_r:
            if type_l != type_r and {type_l, type_r} == {int, float}:
                self.add_error(node, f"Mixed-type literal math operation ({type_l.__name__} and {type_r.__name__}) detected. PikaScript does not support implicit type promotion (causes instruction hangs). Cast your types explicitly (e.g. float(x)).")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        # Warn on list indices modification (e.g. results[idx] = score)
        if isinstance(node.ctx, ast.Store):
            self.add_warning(node, "List item assignment ('list[idx] = val') detected. PikaScript has high heap allocation overhead for list mutations, which can cause silent memory exhaustion. Use individual flat variables for logging parameters.")
        self.generic_visit(node)

def lint_file(file_path, script_only=True):
    if not os.path.exists(file_path):
        print(print_colored(f"[Error] File not found: {file_path}", "red"))
        return False, 1

    file_size = os.path.getsize(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # Parse Abstract Syntax Tree
    try:
        root = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        print(print_colored(f"[Syntax Error] Failed to parse script: {e.msg} at line {e.lineno}", "red"))
        return False, 1

    visitor = PikaLintVisitor()
    visitor.visit(root)

    # Compile findings
    errors = visitor.errors
    warnings = visitor.warnings


    # Add size-related warnings/errors
    if file_size >= 4096:
        if script_only:
            errors.append((0, f"File size is {file_size} bytes (>= 4096 bytes). Script-Only dynamic upload will fail with a silent compiler buffer overflow. You must compile this script directly into the firmware using 'deploy.py' (omit --script-only) or shrink the file."))
        else:
            warnings.append((0, f"File size is {file_size} bytes (>= 4096 bytes). Large Python scripts consume on-chip flash memory when compiled into the C binary. Check for unused functions or logs."))
    elif file_size >= 3000:
        warnings.append((0, f"File size is {file_size} bytes (>= 3000 bytes). This is approaching PikaScript's parsing memory threshold. Keep the file small or compile it directly into the binary to avoid boot crashes."))

    # Print results
    print(print_colored(f"--- PikaLint: {os.path.basename(file_path)} ---", "bold"))
    
    if not errors and not warnings:
        print(print_colored("✔ No compatibility issues found. Script is fully compatible with PikaScript!", "green"))
        print()
        return True, 0

    # Sort messages by line number
    all_issues = []
    for line, msg in errors:
        all_issues.append((line, "ERROR", msg))
    for line, msg in warnings:
        all_issues.append((line, "WARNING", msg))
    all_issues.sort(key=lambda x: x[0])

    for line, issue_type, msg in all_issues:
        line_str = f"Line {line:3d}: " if line > 0 else "Global:   "
        if issue_type == "ERROR":
            print(f"{print_colored(line_str, 'bold')}[{print_colored('ERROR', 'red')}] {msg}")
        else:
            print(f"{print_colored(line_str, 'bold')}[{print_colored('WARNING', 'yellow')}] {msg}")

    print()
    if errors:
        print(print_colored(f"✖ Found {len(errors)} error(s) and {len(warnings)} warning(s). Compilation/boot on the physical board will fail.", "red"))
        return False, len(errors)
    else:
        print(print_colored(f"⚠ Found {len(warnings)} warning(s). Code should run, but optimize for memory/safety.", "yellow"))
        return True, 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/pikalint.py <file_path>")
        sys.exit(1)
        
    success, error_count = lint_file(sys.argv[1])
    sys.exit(error_count)
