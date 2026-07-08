# EEE3097S / EEE3098S / EEE3099S: Design Report Template
*Graduate Attribute 3 (Design) Assessment Portfolio*

**Student Name:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**Student Number:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**Degree Stream:** [Electrical / ECE / Mechatronics]  
**Report Number:** [Report 1 / Report 2]  
**Design Subsystem Topic:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  

---

## 1. Brief Description of Design Task
*Provide a concise overview of the specific engineering problem you are solving and the subsystem you are designing (e.g., speed feedback control, sensor fusion, line sensor correction, safety wrapper, etc.). Explain how this fits into the broader system architecture of the autonomous mouse.*

---

## 2. Visual Aids for this Report
*Insert all relevant figures, diagrams, flowcharts, or scope captures here. These must be referenced explicitly in the text below. Useful diagrams include:*
*   *Block diagrams showing system signal flow, interfaces, and inputs/outputs.*
*   *Stateflow logic charts or algorithmic flowcharts.*
*   *Simulink controller models or C-code software structure.*
*   *Oscilloscope wave captures or telemetry data plots.*

---

## 3. Design Criteria and Constraints (Maps to ECSA Criterion 3.1)
*Formulate a clear design brief. Specify:*
*   **Quantitative Design Criteria**: Desired performance standards (e.g., heading error $< 2^\circ$ after a 90° turn, speed regulation settling time $< 100\text{ ms}$, line sensor response delay $< 5\text{ ms}$).
*   **Physical and Computational Constraints**: Limits on hardware/software interfaces (e.g., STM32 CPU control execution time limits $< 10\text{ ms}$, memory footprints, ADC sampling limits, power constraints, safety distances).

---

## 4. Main Design Assumptions with Justification (Maps to ECSA Criterion 3.1 & 3.3)
*State your engineering assumptions and justify them mathematically or physically. Examples include:*
*   *Assuming motor gains are linear within the operating region (with justification based on motor voltage ranges).*
*   *Assuming Gaussian white noise on sensor rails (with justification based on telemetry logs).*
*   *Assuming flat surfaces and perfect tire-floor traction (and how slip exceptions are handled).*

---

## 5. Design Process & Alternative Solutions (Maps to ECSA Criterion 3.2)
*Describe the structured approach used to research, brainstorm, and select your solution. You must:*
*   **Identify Alternatives**: Document at least two distinct engineering approaches or algorithms to solve the problem (e.g., a simple Proportional controller vs. a Proportional-Integral-Derivative controller, or a complementary filter vs. a Kalman filter).
*   **Evaluate Alternatives**: Evaluate them against your quantitative criteria and constraints (using a trade-off matrix or qualitative comparisons).
*   **Select Preferred Solution**: Justify why the selected approach is the optimal engineering choice.

---

## 6. Design Implementation & First-Principles Modeling (Maps to ECSA Criterion 3.3)
*Perform the detailed engineering design. Show the mathematical formulation and logical layout from first principles, including:*
*   *System equations (e.g., differential-drive kinematics, motor electrical and mechanical dynamic equations).*
*   *Control laws (e.g., discrete z-domain transfer functions, PID discretization).*
*   *Algorithm code schemas (e.g., C-caller interface logic or flowchart transitions).*

---

## 7. Design Evaluation, Testing & Discussion (Maps to ECSA Criterion 3.4 & 3.5)
*Document the validation of your design. You must:*
*   **Verify Performance**: Present experimental data (from virtual co-simulation or physical serial logs) demonstrating how the design performs.
*   **Test under Perturbations**: Verify the controller's robustness under realistic perturbations (e.g., simulated motor asymmetry, wheel slip, or measurement noise).
*   **Critically Evaluate**: Evaluate the final performance against the criteria defined in Section 3. Discuss any deviations from theoretical models, design failures, and limitations of the current design.

---

## Appendix: ECSA Graduate Attribute 3 (Design) Rubric Mapping

To ensure your report provides bulletproof evidence for ECSA accreditation audits, use this table as a checklist to verify that your sections satisfy all GA3 assessment criteria:

| ECSA GA3 Assessment Criterion | Report Section | What the Auditor Looks For |
| :--- | :--- | :--- |
| **Criterion 3.1: Problem Definition & Constraints** | **Section 3**: `Design Criteria and Constraints`<br>**Section 4**: `Main Design Assumptions with Justification` | A clear design brief outlining quantitative performance targets and physical/computational limits (e.g. CPU, memory, power). |
| **Criterion 3.2: Generation & Evaluation of Alternative Solutions** | **Section 5**: `Design Process & Alternative Solutions` | Documented generation of at least two alternative design concepts and a structured trade-off matrix/justification for the chosen concept. |
| **Criterion 3.3: Detailed Design & Modeling (First-Principles)** | **Section 6**: `Design Implementation & First-Principles Modeling`<br>**Section 4**: `Main Design Assumptions` | Detailed mathematical formulations (kinematics, transfer functions, discrete z-domain control laws) or logic models (state charts) from engineering science. |
| **Criterion 3.4: Implementation & Experimental Verification** | **Section 7**: `Design Evaluation, Testing & Discussion` | Successful implementation of the design and testing under realistic physical perturbations (motor asymmetry, traction loss/slip, and measurement noise). |
| **Criterion 3.5: Design Evaluation & Discussion** | **Section 7**: `Design Evaluation, Testing & Discussion` | Critical analysis of final experimental data against target criteria, analysis of model deviations, and discussion of design limits and failures. |
