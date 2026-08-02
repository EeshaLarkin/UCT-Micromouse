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

\usepackage{amsmath}
\usepackage{amssymb}

% Set system Helvetica font using fontspec under XeLaTeX
\usepackage{fontspec}
\setmainfont{Helvetica}
\setsansfont{Helvetica}
\setmonofont{Courier}
\renewcommand{\familydefault}{\sfdefault}

% Render math equations using the main text font (Helvetica) to prevent missing glyphs
\usepackage[italic]{mathastext}

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

    # Determine paths relative to repository root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    rel_path = os.path.relpath(md_file, repo_root)
    tex_rel_path = rel_path.replace('_', r'\_')
    github_url = f"https://github.com/nicollsf/UCT-Micromouse/blob/main/{rel_path}"

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Construct the injected header warning banner using a native LaTeX box
    injected_header = (
        "\\noindent\\fbox{\n"
        "\\begin{minipage}{\\dimexpr\\textwidth-2\\fboxsep-2\\fboxrule\\relax}\n"
        "\\medskip\n"
        "\\hspace{10pt}\\textbf{\\textcolor{primary}{Static PDF Export Notice}}\n"
        "\\vspace{0.5em}\\\\\n"
        "\\hspace{10pt}This PDF was generated on \\texttt{" + timestamp + "}. The definitive, live master version\\\\\n"
        "\\hspace{10pt}of this document is maintained in Markdown (\\texttt{.md}) format at:\\\\\n"
        "\\hspace{10pt}\\textbf{Link to Master Source:} \\href{" + github_url + "}{" + tex_rel_path + "} \\\\\n\n"
        "\\hspace{10pt}\\textit{Students are advised to run \\texttt{git pull --recurse-submodules} in their}\\\\\n"
        "\\hspace{10pt}\\textit{workspaces to receive the latest updates. In case of discrepancy,}\\\\\n"
        "\\hspace{10pt}\\textit{the repository \\texttt{.md} file is the master reference.}\n"
        "\\medskip\n"
        "\\end{minipage}\n"
        "}\n\n"
        "\\vspace{1.5em}\n\n"
    )

    output_pdf = md_file.rsplit('.', 1)[0] + '.pdf'
    
    print(f"=== Compiling Styled PDF: {os.path.basename(md_file)} ===")
    
    # Create a temporary preamble file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
        f.write(create_latex_preamble())
        preamble_path = f.name

    # Create a temporary markdown file with the warning banner injected
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md:
        with open(md_file, 'r', encoding='utf-8') as original_f:
            temp_md.write(injected_header)
            temp_md.write(original_f.read())
        temp_md_path = temp_md.name

    try:
        # Build command using xelatex engine for system font support
        cmd = [
            "pandoc",
            temp_md_path,
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
        # Clean up temporary files
        if os.path.exists(preamble_path):
            os.remove(preamble_path)
        if os.path.exists(temp_md_path):
            os.remove(temp_md_path)

if __name__ == "__main__":
    main()
