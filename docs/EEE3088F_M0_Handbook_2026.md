# **M0: Course Handbook & Project Specifications**

**Course:** EEE3088F (2026)  
**Project:** Acoustic Direction of Arrival (DoA) Sensor

---

## **1\. Course Philosophy: The Forensic Engineering Model**

This course operates on a "Design-First, Theory-Later" pedagogy. Students are required to commit to hardware and firmware designs (M1/M2/M3) before all the formal theory is fully lectured. The core learning occurs through the gap between your design intent and the physical reality of the M4 test results. Milestone 5 is structured to reward technical diagnosis and "Honest Failure" over a lucky success.

Students are assessed on their ability to translate user requirements into technical specifications. Every milestone requires the submission of diagrammatic evidence (block diagrams, context diagrams) and acceptance testing procedures (ATPs). These artifacts serve as the formal record of system integration and are weighted equally with hardware performance.

---

## **2\. Project Overview**

The objective of EEE3088F is to design, manufacture, and validate a custom PCB sensor capable of detecting the angle of a single-tone acoustic source. The course is structured as a professional engineering workflow, moving from a technical contract to a manufactured hardware gate, and finally to individual firmware implementation and forensic analysis.

### **Collaboration Model:**

* **Design Phase (M1-M2):** Performed in **Pairs**. Students share the hardware design and sourcing responsibility.  
* **Implementation & Analysis Phase (M3-M5):** Performed **Individually**. Each student must develop their own firmware and conduct their own forensic audit of the shared hardware.

---

## **3\. Technical Law: The Physical Constraints**

To ensure compatibility with the EEE3088F Automated Testing Rig, all designs must adhere to the following constraints. Failure to meet these "Hard Gates" will result in a design that cannot be tested.

* **Mechanical Interface:** Two mounting holes with a center-to-center pitch of exactly **50.0mm**. Holes should be sized for M3 bolts (3.2mm diameter).  
* **Electrical Standard:** All components and logic must be strictly 3.3V compatible. The use of 5V power or 5V I2C logic pull-ups is prohibited to ensure Rig safety and cross-compatibility.  
* **Electronic Law (Analog Requirement):** To satisfy the signal conditioning objectives of the course, the **Mandatory Reference Pair must be analog**. The use of digital-output microphones (e.g., I2S, PDM) for the reference pair is **strictly prohibited**. Your design must demonstrate a complete analog signal chain (Amplification → Filtering → DC Biasing) interfaced with the MCU’s internal ADC.  
* **Acoustic Law (Ground Truth):** The Testing Rig is calibrated to a "Whisper" environment to maintain lab functionality. All Milestone 1 physics proofs and Milestone 2 hardware designs must be based on:  
* **Standard Input:** 67 dB SPL ([![][image1]](https://www.codecogs.com/eqnedit.php?latex=p_%7Brms%7D%20%5Capprox%200.045%20%5Ctext%7B%20Pa%7D#0)).  
* **Design Target:** Your signal chain must map this input to an ADC voltage swing of **0.8V – 1.2V Peak-to-Peak**, centered at a **1.65V DC Bias**.  
* **Sensor Reference Axis:** The physical line connecting the centers of the two mounting holes.  
* **Reporting Boresight ([![][image2]](https://www.codecogs.com/eqnedit.php?latex=0%5E%7B%5Ccirc%7D#0)):** The perpendicular line passing through the midpoint of the Reference Axis, directed "forward" from the board.  
* **Mandatory Reference Pair:** Every board **must** contain at least one microphone pair ([![][image3]](https://www.codecogs.com/eqnedit.php?latex=M_%7Bref1%7D#0),[![][image4]](https://www.codecogs.com/eqnedit.php?latex=M_%7Bref2%7D#0)) positioned symmetrically on the Reference Axis, equidistant from the origin (midpoint).  
* **PCB Size Limit:** The maximum allowable board dimension is 100mm x 100mm.

---

**4\. Acoustic Reference Specifications**

To simulate a realistic search-and-rescue environment while maintaining a professional lab atmosphere, all designs must adhere to the following acoustic constraints:

* **Standard Input:** **67 dB SPL** at the microphone face.  
* **Reference Pressure (prms​):** Exactly **0.045 Pa** (calculated against p0​=20μPa).  
* **Electronic Design Target:** Your analog signal chain must map this 67 dB input to a peak-to-peak voltage (Vpp​) between **0.8V and 1.2V**.  
* **DC Operating Point:** The signal must be biased at **1.65V** (VCC/2).  
* **Localization Budget:** You must resolve the Direction of Arrival (DoA) within a **50ms** window at this signal level.

**Warning:** Designing for 67 dB requires a total system gain of approximately **60–63 dB**. Students must pay close attention to the **Gain-Bandwidth Product (GBW)** of their chosen Op-Amps and are strongly encouraged to use a **two-stage amplification** strategy to maintain stability and minimize noise.

---

## **4\. Rig Interface: Communication & Power Header**

The board must incorporate a 4-pin male 2.54mm pitch "Communication & Power" header, placed at the board edge for interfacing with the Automated Rig:

* Pin 1: GND (Ground)  
* Pin 2: VCC (3.3V DC Input ONLY). The Automated Rig provides a regulated 3.3V supply (max 300mA). Boards requiring 5V will not function and will be rejected at the M2 Manufacturing Gate.  
* Pin 3: SDA (I2C Data Line)  
* Pin 4: SCL (I2C Clock Line).  
* Pin 3 & 4: SDA/SCL (3.3V Logic). I2C communication is strictly 3.3V. On-board pull-up resistors must be tied to the 3.3V rail.

---

## **5\. System Integration: I2C Interface Specification**

The sensor acts as an I2C Slave at **Address 0x42**. This section defines the formal **Interface Control Document (ICD)** for the communication link between the sensor and the Automated Rig.

### **5.1 Register Mapping (The Data Interface)**

The following registers constitute the primary **Technical Specifications** for the data exchange.

| Register | Name | Data Type | Description |
| :---- | :---- | :---- | :---- |
| **0x00** | SYS\_STATUS | uint8 | 0x01: Trigger, 0x02: Busy, 0x03: Ready |
| **0x04-0x07** | FREQ\_CONTRACT | float32 | Contracted [![][image5]](https://www.codecogs.com/eqnedit.php?latex=f_t#0) (Little-Endian) |
| **0x08** | DOA\_ANGLE | int8 | Angle relative to boresight  ([![][image6]](https://www.codecogs.com/eqnedit.php?latex=-90%5E%7B%5Ccirc%7D#0) to [![][image7]](https://www.codecogs.com/eqnedit.php?latex=%2B90%5E%7B%5Ccirc%7D#0)) |
| **0x0C** | CONFIDENCE | uint8 | Signal Quality/Correlation Strength (Range: 0-100) |
| **0x10-0x18** | STUDENT\_ID | string | Unique Student Number (ASCII) |

### **5.2 The Handshake Protocol (Functional State Specification)**

To ensure deterministic interaction with the Automated Testing Rig, the sensor must implement a three-state behavioral model. This protocol ensures the Rig harvests data only when the signal processing is complete and valid.

1. The READY State (SYS\_STATUS=0x01): Upon successful power-on and initialization, the sensor must enter the **READY** state. In this state, the sensor is "listening" to the I2C bus. The Rig may perform a **Discovery Read** of the `STUDENT_ID` or `FREQ_CONTRACT` at any time. The sensor remains in this state until it receives a **Trigger Command**.  
2. The BUSY State (SYS\_STATUS=0x02): The handshake is initiated when the Rig writes the value 0x02 to the `SYS_STATUS` register. This is the "Starting Gun."  
   * **Immediate Action:** The firmware must immediately begin its acoustic sampling window.  
   * **Lock-out:** While in the **BUSY** state, the sensor must prioritize the DSP algorithm and ignore any further I2C writes to the status register.  
   * **Latency:** The transition out of this state is governed by the **50ms Latency Ceiling**.  
3. The DONE State (SYS\_STATUS=0x03): Once the DoA calculation is complete, the firmware must first populate the `DOA_ANGLE` and `CONFIDENCE` registers with the new data. Only *after* the data registers are updated should the firmware set `SYS_STATUS` to 0x03.  
   * **Data Harvest:** The Rig polls the status register; the moment it detects  
      0x03, it will read the result registers.  
   * **Reset:** After the Rig has successfully harvested the data, the sensor should reset itself back to the **READY** (0x01) state to await the next test cycle.  
     

### **5.3 Interface Timing Specifications**

Compliance with these timing gates is required for successful **Acceptance Testing (ATP-SW-03)**.

| Phase | Constraint | Technical Specification |
| :---- | :---- | :---- |
| **Boot Latency** | Max time to `READY` (0x01) | ≤10s |
| **Trigger Jitter** | Max time to `BUSY` (0x02) | ≤50ms |
| **Total Latency** | Trigger (0x02) to Done (0x03) | ≤50ms |
| **Bus Integrity** | Max Clock Stretching | ≤100μs |

#### **Tips for I2C Success:**

* **Interrupt-Driven Writes:** Use an I2C interrupt to catch the Rig’s `0x02` (Trigger) write immediately.  
* **Atomic Updates:** Ensure `DOA_ANGLE` and `CONFIDENCE` are fully updated before you flip `SYS_STATUS` to `0x03`.

---

## **6\. Deliverables & Milestones**

* **M1 (Technical Contract):** Individual submission of Requirement Traceability, physics proofs, and signal chain design.  
* **M2 (PCB Design):** Team submission of Gerber files, BOM, and a budget quote for 2 units.  
* **M3 (Firmware Strategy):** Individual proof of I2C compliance and submission of Software Acceptance Test Procedures (ATPs).  
* **M4 (Gauntlet Validation):** Individual performance log and identity verification video.  
* **M5 (Final Report):** IIndividual performance log and execution of the Pre-Validation Hardware ATP.

---

## **7\. Administrative Policies**

* **Submission Format:** All documents must be submitted via Gradescope using the provided boxed templates.  
* **Late Policy:** Hard gates (M2 and M3) have zero-tolerance for lateness as they are tied to fabrication and testing schedules.  
* **Academic Integrity:** While hardware is shared, all code (M3), logs (M4), and reports (M5) must be individual work. Use of a partner's code or log file will be treated as plagiarism.  
* **Design for Manufacture (DFM) Checks:** The submitted Gerber files must pass all common Design Rule Checks (DRC) and adhere to the following minimum JLC PCB requirements (failure to meet these constitutes a critical DRC error):  
* Minimum Trace Width: **0.25mm**  
* Minimum Clearance (Trace to Trace/Pad): **0.25mm**  
* Hole Sizes: Minimum **0.3mm**, Maximum **6mm**  
* All components must have a confirmed **"In-Stock"** status on the JLCPCB portal at the time of submission.  
* **The Budget Gate:** Designs exceeding the provided budget for two assembled units in M2 will not be manufactured.  
* **Voltage Compliance Audit:** Gerber files and BOMs will be audited for 5V-to-3.3V compatibility. Any design utilizing 5V logic levels or 5V-only sensors (e.g., non-compliant microphones or LCDs) will be issued an immediate **REJECTED / RESUBMIT** status.  
* **Hardware Access:** Students are responsible for the safekeeping of their pair's boards. Replacements for lost or damaged boards will not be provided by the department.  
* **The One-Shot Fabrication Rule:** If your M2 PCB Design submission is rejected twice by the fabrication house (e.g., critical DRC error or budget violation), you move to the Fallback (Dev Board) Option and incur a **flat 20% penalty** on your M4 Rig Validation score.  
* **Fallback (Dev Board) Option:** This serves as a contingency platform. Should your custom PCB become non-functional after M2 submission, this option allows you to transfer your core firmware to your STM development board and still complete the M4 Automated Rig Test. While a penalty is incurred, this ensures you can demonstrate proficiency in the firmware, validation, and reflection milestones (M3, M4, M5), avoiding a total project failure.  
* **The Forensic Clause:** Marks lost in M4 for poor performance (high MAE) can be recovered in M5 by providing quantifiable evidence from your Test Points to prove the specific root-cause of your failure.  
* **Interface Control:** The **Interface Table** provided in M2 is a binding document. If your physical PCB pinout deviates from your Interface Table, the board will be rejected.  
* **Acceptance Testing (ATP) Compliance:** Milestone grades are contingent on the submission of formal ATP results. A "working" board with a missing or faked ATP table will incur a professional standards penalty.

## ---

**8\. Prototyping & Isolation**

Before committing to a finalized PCB design, students should use their microprocessor board to prototype the signal chain on a breadboard. This allows for immediate verification of microphone biasing and gain stages. By establishing this "known-good" setup early, you can isolate firmware bugs from hardware faults. If your custom PCB fails, this breadboard serves as your Fallback platform for M4.

---

## **9\. Project milestone summary**

### **M1: Technical Contract (10%)**

* **The Task:** Submit a formal technical proposal and physics proof.  
* **Collaboration:** Team-based data; Individual-based justification.  
* **The Logic:** You must justify your Target Frequency ([![][image8]](https://www.codecogs.com/eqnedit.php?latex=f_t#0)) and prove that your proposed microphone spacing ([![][image9]](https://www.codecogs.com/eqnedit.php?latex=d#0)) satisfies the **ULA physics baseline**. This serves as your "Contract" with the Rig; the Rig will play the frequency you declare here.  
* **The Gate:** Incorrect aliasing math or unrealistic ADC sampling rates ([![][image10]](https://www.codecogs.com/eqnedit.php?latex=f_s#0)) will result in a resubmission.

### **M2: PCB Design & Sourcing (20%)**

* **The Task:** Submit your production-ready Gerber files, BOM, and budget quote.  
* **Collaboration:** Performed in Pairs.  
* **The Gate:** This is the Manufacturing Gate. Your board must pass the 50.0mm mounting pitch check, the 3.3V electrical compatibility audit, and include all 6 mandatory Test Points (including TP-VCC).  
* **The Rule:** You have **one chance** to manufacture. If the design is rejected twice for DRC errors or budget violations, you move to the Fallback Option (-20% penalty).

### **M3: Firmware Strategy & DSP Prototype (20%)**

* **The Task:** Verify your I2C handshake and DoA algorithm using the GitHub Autograder.  
* **Collaboration:** Strictly Individual.  
* **The Logic:** You must prove your code can set the "Ready" bit within the **50ms latency ceiling**.  
* **Deliverable:** A successful "Green Checkmark" from the Autograder and a Cross-Correlation (CCF) plot verifying your math on "Golden Traces."

### **M4: Gauntlet Validation (30%)**

* **The Task:** Live performance validation of your individual firmware on the manufactured hardware.  
* **Collaboration:** Strictly Individual.  
* **The Score:** The Rig reads your unique Student ID and frequency, then measures your accuracy across a 180° sweep. Marks are scaled based on your **Mean Absolute Error (MAE)**.  
* **The "Red Line":** Any single measurement taking longer than 50ms results in an automatic 0 for that run.

### **M5: Forensic Audit & Final Report (20%)**

* **The Task:** A 3-page engineering post-mortem and technical reflection.  
* **Collaboration:** Strictly Individual.  
* **The Analysis:** Use the mandatory Test Points (**TP-SIGNAL**, **TP-BIAS**) to quantify SNR and power ripple.  
* **The Recovery:** Use the **Forensic Clause** to recover marks lost in M4 by proving exactly *why* your hardware failed and proposing a "Version 2.0" fix.

---

### **The EEE3088F Assessment Roadmap**

| Milestone | Phase | Evaluator | Focus | Weight |
| :---- | :---- | :---- | :---- | :---- |
| **M1: Selection** | Research | **Instructor** | Physics validity (λ/2) and contract feasibility. | 10% |
| **M2: Review** | DFM | **TA (Manual)** | Mechanical alignment (50mm) and Budget compliance. | 20% |
| **M3: Math** | Algorithmic | **GitHub (Auto)** | 50ms timing compliance and I2C register integrity. | 20% |
| **M4: Rig** | Validation | **Test Rig (Auto)** | Real-world accuracy (MAE) and Student ID discovery. | 30% |
| **M5: Reflection** | Forensic | **Instructor** | Root-cause diagnosis and "Honest Engineer" bonus. | 20% |

# **M0: Consolidated TA Grading Memo (2026)**

**Role:** Standardized, high-resolution marking criteria and deduction logic.

### ---

**M1: Technical Contract & Physics Baseline**

| Look-For | Gold Standard (100%) | Deduction Logic | Critical Fail |
| ----- | ----- | ----- | ----- |
| **Contracted f\_t** | 1–5 kHz. Justification cites Mic datasheet SNR or lab noise. | \-3 Points: f\_t in Block 2 (Math) does not match Contract Value in Block 1\. | f\_t is out of range (e.g., 10 kHz). |
| **Physics Proof** | Correctly calculates Aliasing Angles. Must acknowledge d \> lambda/2 if chosen. | \-5 Points: Chooses f\_t \> 3.43 kHz but claims "no aliasing." | Incorrect speed of sound (e.g., uses 340 m/s instead of 343 m/s). |
| **Signal Chain** | Quantitative Gain (e.g., 45dB). Explicit Biasing (Vcc/2). Clipping risk addressed. | \-2 Points: Use of qualitative terms (e.g., "High gain"). No mention of DC bias. | No signal chain logic; doesn't understand ADC requirements. |

A-Grade Benchmark: "We selected 2.5 kHz to maximize the SNR while maintaining d \< lambda/2 (68.6 mm), ensuring a full 180° alias-free field of view for the Rig."

**Hardware Viability:** Students must prove their planned Sampling Rate ([![][image11]](https://www.codecogs.com/eqnedit.php?latex=f_s#0)) is at least twice their contracted frequency ([![][image12]](https://www.codecogs.com/eqnedit.php?latex=f_t#0)).

**Component Audit:** Must include a Pugh Matrix comparing at least three microphone options based on SNR, ease of assembly (LGA vs. Lead), and cost.

---

### **M2: PCB Design & Sourcing**

| Look-For | Gold Standard (100%) | Deduction Logic | Critical Fail |
| ----- | ----- | ----- | ----- |
| **Mounting Pitch** | Screenshot shows center-to-center dimensioning at 50.0 ± 0.2mm. | TAs should count grid squares if the dimension tool is missing. | Pitch is visually wrong (e.g., 20mm). |
| **Test Points (TPs)** | All 5 TPs present, labeled in silkscreen, and accessible (not under ESP32). | \-2 Points per Missing TP (VCC, GND, BIAS, SIGNAL, I2C). | No TPs. Forensic audit in M5 will be impossible. |
| **DRC/BOM** | Report shows 0 shorts/opens. Power traces \> 0.5mm. In-stock parts. | \-4 Points: If Mic or Op-Amp footprint is incorrect. | Fatal DRC errors (unconnected nets) or pitch is not 50.0mm. |

Look-For Deduction: If the ESP32 is soldered directly over the Test Points, deduct 5 marks for "Inaccessibility."

### ---

**M3: Firmware Strategy & DSP Prototype**

| Look-For | Gold Standard (100%) | Deduction Logic | Critical Fail |
| ----- | ----- | ----- | ----- |
| **I2C Discovery** | Code uses union or memcpy. Little-endian verified. Passing Autograder. | \-10 Points (Fatal): If the GitHub I2C Discovery test fails. | Fails Autograder (Float is corrupted or Big-Endian). |
| **Timing Budget** | Sum of (Sample \+ Calc \+ I2C) \< 50ms. Realistic math. | \-5 Points: If the Timing Budget is idealistic (e.g., ignores I2C interrupt time). | Sampling alone takes \> 50ms. |
| **Artifacts** | CCF plot is clearly shown and annotated with sample-delay/time. | \-3 Points: Polarity inversion (Mic A lead \= Positive). | Failure to provide the CCF artifact or a realistic Timing Budget. |

A-Grade Benchmark: "To hit the 50ms deadline, we sample 512 points at 20 kHz (25.6 ms). This leaves 24.4 ms for the FFT and I2C reporting, providing a 15% safety margin."

### ---

**M4: Rig Validation & Performance**

| MAE Score | % of 30% Rig Score | Deduction Logic | Critical Fail |
| ----- | ----- | ----- | ----- |
| **MAE \<= 5°** | 100% | \-5 Points: If "Proof of Life" video does not show the board physically mounted. | I2C Failure (cannot read ID or f\_t) or any single Latency \> 50ms. |
| **5° \< MAE \<= 15°** | 70% | \-5 Points: If LED stays "Busy" while the Rig is moving (Timing violation). | No Data/NACK. |
| **MAE \> 15°** | 40% (Credit for Comm. only) | \-7 Points: If the Target vs. Measured plot does not match the student's unique Rig Log (AI-Killer Check). | N/A |

The Red Lines (Automatic M4 Disqualification):

* Bus Hang: If the board holds the SCL line low (Clock Stretching) for more than 10ms, the Rig aborts to prevent hardware damage.  
* Deceptive Engineering: If the board reports CONFIDENCE \= 100 but the angle error is \> 30°, the student is flagged for a manual audit to check for hard-coded/fake results.

### ---

**M5: Forensic Audit & System Reflection**

| Look-For | Gold Standard (100%) | Deduction Logic | Critical Fail |
| ----- | ----- | ----- | ----- |
| **Signal/Bias Evidence** | Scope captures of TP-SIGNAL/TP-BIAS are quantified (Vpp, mV ripple, SNR) and support the diagnosis. | \-8 Points: Using descriptive terms like "noisy" or "small" without numbers. | Image is not of a signal or is unreadable. |
| **Root Cause** | Specific technical failure is linked to the evidence (e.g., "Noise on TP-BIAS caused jitter"). | \-5 Points: If the "Root Cause" is not visible in the scope captures. | Blames the Rig without evidence. |
| **Version 2.0 Fix** | Proposes one specific Hardware Fix and one specific Firmware Fix. | \-4 Points: If scope captures lack a time-base or voltage scale. | N/A |

A-Grade Benchmark (M5 Block 2 Example): "TP-BIAS showed a noise floor of 240 mVpp at a frequency of 1.2 MHz. This correlates with the switching frequency of the LM2596 regulator. Because our ADC reference was bouncing by ±120 mV, our phase-detection logic saw a 'jitter' of ±8°, which matches the noise seen in our M4 Rig Log."

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAAANBAMAAACDcvdnAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMAVKvN74lEInYy3WYQmbv8EmWgAAAAHElEQVR4XmP8z0AeYEIXIBaMasQDRjXiAWRrBAAJzwEZl4R3GAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMBAMAAACkW0HUAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMAMnarzd3vRFS7ZhCJmSKMG7yZAAAAEUlEQVR4XmP8zwACTGCSShQAVvEBF2ROGQoAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAQBAMAAACMxcAQAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARM27Imbvmat2EDLdiVRWT+/bAAAAE0lEQVR4XmP8z4AOmNAFRoUQAABCEAEfMGwXMgAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAQBAMAAABjB6suAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARM27Imbvmat2EDLdiVRWT+/bAAAAFklEQVR4XmP8z4AOPjKhiwDBqBh2MQBufAIQxOUPiwAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAPBAMAAADAEygDAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARInN71QQdpkiZrur3TKR0mKdAAAAFElEQVR4XmP8zwAEH5lAJAMDDSkAy1sCDogdkgsAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAMBAMAAADxOqKKAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMAMrvviXaZzd1mECKrRFQ09iNxAAAAEklEQVR4XmP8z4AKmND4Q0gAANSRARfVNXU2AAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAMBAMAAADxOqKKAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMAme/dZnYizYlURLsQMqt0m//QAAAAEklEQVR4XmP8z4AKmND4Q0gAANSRARfVNXU2AAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAPBAMAAADAEygDAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARInN71QQdpkiZrur3TKR0mKdAAAAFElEQVR4XmP8zwAEH5lAJAMDDSkAy1sCDogdkgsAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAALBAMAAACwtdEWAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMAECIyVHaJq7vN70SZ3WY3t8peAAAAEUlEQVR4XmP8z8DAwMRAKgEAOF4BFfMYOykAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAPBAMAAAAizzN6AAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARInN71QQdpkiZrur3TKR0mKdAAAAEUlEQVR4XmP8zwACTGCSlhQAbigBHV8/R9QAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAPBAMAAAAizzN6AAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARInN71QQdpkiZrur3TKR0mKdAAAAEUlEQVR4XmP8zwACTGCSlhQAbigBHV8/R9QAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAPBAMAAADAEygDAAAAMFBMVEX///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAv3aB7AAAAD3RSTlMARInN71QQdpkiZrur3TKR0mKdAAAAFElEQVR4XmP8zwAEH5lAJAMDDSkAy1sCDogdkgsAAAAASUVORK5CYII=>