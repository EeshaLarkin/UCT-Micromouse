#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile

def create_latex_preamble():
    # Custom LaTeX preamble to override default Pandoc styling with modern aesthetics
    return r"""
\usepackage{geometry}
\geometry{margin=0.8in}

% Set Helvetica as the default sans-serif font and make it the main document font
\usepackage[scaled]{helvet}
\renewcommand\familydefault{\sfdefault}
\usepackage[T1]{fontenc}

\usepackage{xcolor}
\definecolor{primary}{HTML}{1A365D}   % Dark Navy
\definecolor{secondary}{HTML}{2B6CB0} % Slate Blue
\definecolor{charcoal}{HTML}{2D3748}  % Body text

\usepackage{titlesec}
\titleformat{\section}{\color{primary}\normalfont\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\color{secondary}\normalfont\large\bfseries}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\color{secondary}\normalfont\normalsize\bfseries}{\thesubsubsection}{1em}{}

% Custom footer and headers
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\color{charcoal}\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Line spacing and paragraph skips
\usepackage{setspace}
\setstretch{1.15}
\usepackage{parskip}

% Styling links
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=secondary,
    filecolor=secondary,      
    urlcolor=secondary,
}
"""

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/compile_docs.py <markdown_file>")
        print("Example: python tools/compile_docs.py docs/assignments/milestone1_instructions.md")
        sys.exit(1)

    md_file = os.path.abspath(sys.argv[1])
    if not os.path.exists(md_file):
        print(f"[Error] Source file not found: {sys.argv[1]}")
        sys.exit(1)

    output_pdf = md_file.rsplit('.', 1)[0] + '.pdf'
    
    print(f"=== Compiling Styled PDF: {os.path.basename(md_file)} ===")
    
    # Create a temporary preamble file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
        f.write(create_latex_preamble())
        preamble_path = f.name

    try:
        # Build command using xelatex engine for system font support
        cmd = [
            "pandoc",
            md_file,
            "-o", output_pdf,
            "--pdf-engine=xelatex",
            f"--include-in-header={preamble_path}"
        ]
        
        print(f"Running pandoc compilation...")
        subprocess.run(cmd, check=True)
        print(f"[Success] PDF generated successfully: {output_pdf}")
    except subprocess.CalledProcessError as e:
        print(f"[Error] Pandoc compilation failed: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary preamble file
        if os.path.exists(preamble_path):
            os.remove(preamble_path)

if __name__ == "__main__":
    main()
