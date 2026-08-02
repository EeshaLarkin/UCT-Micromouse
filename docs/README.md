# **UCT Micromouse Documentation Index & Guide**

This directory contains the complete reference documentation for the UCT Micromouse project. 

> [!IMPORTANT]
> **Definitive Source of Truth:**
> All files in this repository ending in `.md` (Markdown format) represent the single, definitive source of truth for course instructions, rubrics, and technical guides. Any PDF versions distributed on D2L (Amathuba) are compiled directly from these Markdown files. Always pull the latest repository updates (`git pull --recurse-submodules`) to ensure your documentation remains accurate and up-to-date.

---

## **How to Read Markdown (.md) Files**

Markdown files are plain-text documents containing subtle formatting syntax. To read them comfortably with rich styling (headers, bold text, embedded links, and tables), use any of the following renderers:

*   **In Visual Studio Code (Recommended):** Open the `.md` file, then press **`Ctrl+Shift+V`** (Windows/Linux) or **`Cmd+Shift+V`** (macOS) to open the rich graphical Markdown Preview panel.
*   **In Web Browsers:** Install a browser extension such as **Markdown Viewer** (available for Google Chrome, Mozilla Firefox, and Microsoft Edge). Once installed, dragging any local `.md` file into your browser window will render it as a styled webpage.
*   **Via GitHub:** If you view the project workspace on GitHub, all `.md` files render natively into rich, readable formats directly on the repository page.

---

## **Comprehensive Documentation Directory**

Below is the definitive index of all documentation files in this repository:

### **General Course Information**
*   **[README.md](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/README.md) (Root):** The quickstart dashboard for the visual simulator, hardware target outlines, and critical safety rules.
*   **[Course Handbook](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/EEE3097_8_9S_Course_Handbook_2026.md):** The primary master document specifying ECSA Graduate Attribute compliance tracking, graded milestone tasks, chronological submission guidelines, and detailed rubrics.
*   **[Course Plan](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/course_plan_2026.md):** Academic schedule detailing milestones, timelines, design reports, and final demonstrations.

### **Workflow & Developer Guides**
*   **[Milestone 0: Hardware Verification Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assignments/submission0_milestone0_verification.md):** Assembly resources, safety checks, firmware flashing, and dashboard keyboard steering verification instructions.
*   **[Student Workflow Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/student_workflow.md):** The developer setup guide for Python/Simulink, co-simulation execution, firmware deployment over VCP, and debugging strategies.
*   **[Kernel & API Developer Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/kernel_api_guide.md):** Reference documentation detailing the underlying C-Kernel telemetry structure, serial command packet format, and the user-facing Python API.
*   **[Simulink Development & Autograding Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/simulink_guide.md):** Simulink workspace configuration, C-Coder compilation hooks, and virtual testbed loopback socket mapping structures.
*   **[Hardware Setup & Calibration Guide](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/hardware_setup.md):** Peripheral details, motor polarity calibration, and 72 MHz vs 80 MHz clock sweeps.

### **Assignment Submissions (in `/docs/assignments/`)**
*   **[GA Report Guidelines](file:///Users/nicolls/proj/eee3097s/2026/UCT-Micromouse/docs/assignments/gareport_guidelines.md):** Formatting criteria, section-by-section checklists, character limit budgets, and submission rubrics for the two formal Design Reports.