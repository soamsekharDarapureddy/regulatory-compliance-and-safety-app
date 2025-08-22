# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Automotive Regulatory & Safety Compliance Tool", layout="wide")

# === Advanced Prompting: Enhanced CSS for better visual cues ===
st.markdown("""
<style>
:root { --accent:#0056b3; --panel:#f3f8fc; --shadow:#cfe7ff; --pass:#1e9f50; --fail:#c43a31; --info:#7c3aed; }
.card { background:#fff; border-radius:10px; padding:16px; margin-bottom:12px; border-left:8px solid #c9d6e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.card-pass { border-left-color: var(--pass); }
.card-fail { border-left-color: var(--fail); }
.card-info { border-left-color: var(--info); }
.result-pass { color: var(--pass); font-weight:700; }
.result-fail { color: var(--fail); font-weight:700; }
.result-na { color:#808080; font-weight:700; }
.spec-sheet { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
.spec-sheet h4 { margin-top: 0; color: var(--accent); }
.spec-sheet .spec-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #eee; }
.spec-sheet .spec-key { font-weight: 600; color: #333; }
.spec-sheet .spec-value { color: #555; }
a { text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = {
        "reports_verified": 0,
        "requirements_generated": 0,
        "found_component": {},
        "last_pass_rate": "N/A"
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === HEADER ===
logo_col, title_col = st.columns([1, 5])
with logo_col:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.markdown("#### People_TECH")
with title_col:
    st.markdown("""
        <div style="background:var(--accent); padding:10px 22px; border-radius:14px;">
          <h1 style="color:#fff; font-size:1.8em; margin:0; line-height:1.2;">Automotive Compliance & Safety Verification Tool</h1>
          <p style="color:#eaf4ff; margin:0; font-weight:500;">Your Integrated Solution for Validating Automotive Standards</p>
        </div>
    """, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# === KNOWLEDGE BASES ===
KEYWORD_TO_STANDARD_MAP = {
    "safety": "ISO 26262", "asil": "ISO 26262", "fusa": "ISO 26262", "cybersecurity": "ISO/SAE 21434", 
    "tara": "ISO/SAE 21434", "penetration test": "ISO/SAE 21434", "ip rating": "IEC 60529", "ingress protection": "IEC 60529", 
    "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156 / ISO 12405-4", "over-discharge": "AIS-156 / ISO 12405-4", 
    "vibration": "IEC 60068-2-6 / AIS-048", "fatigue": "ISO 4210-6", "braking": "EN 15194 / ISO 4210-2", 
    "emc": "IEC 61000 / ECE R10", "environmental": "ISO 16750", "electrical test": "ISO 16750-2", 
    "mechanical test": "ISO 16750-3", "climatic test": "ISO 16750-4", "can bus": "ISO 11898", "lin bus": "ISO 17987", 
    "ethernet": "IEEE 802.3bw (100BASE-T1)", "diagnostics": "ISO 14229 (UDS)", "autosar": "AUTOSAR Classic/Adaptive Platform", 
    "aspice": "Automotive SPICE (ISO/IEC 330xx)", "misra": "MISRA C/C++ Guidelines", "watchdog": "System Watchdog Functionality Spec",
    "gps": "NMEA 0183 / GNSS Performance Standards", "bluetooth": "Bluetooth Core Specification", "wifi": "IEEE 802.11 Standards",
}

TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage protection": {"purpose": "To verify the device can withstand and protect against voltage levels exceeding its maximum rating.", "requirement": "DUT must survive a specified over-voltage condition for a defined duration without permanent damage or creating a safety hazard.", "pass_fail_criteria": "No physical damage; device is fully functional after test; protection circuits activate as expected.", "equipment": ["Programmable DC Power Supply", "DMM", "Oscilloscope"], "standard_reference": "ISO 16750-2"},
    "short circuit protection": {"purpose": "To ensure the device can safely handle an external short circuit condition.", "requirement": "DUT shall detect and safely interrupt a short-circuit condition within specified time limits without fire or explosion.", "pass_fail_criteria": "Protective measures (fuse, PTC, or electronic switch) activate correctly; device is safe and recoverable after fault removal.", "equipment": ["High-Current Supply", "Oscilloscope", "Shorting Switch"], "standard_reference": "AIS-156 / IEC 62133"},
    "functional safety mechanism": {"purpose": "To verify that a specific safety mechanism (e.g., watchdog) operates according to its design.", "requirement": "The safety mechanism must detect the injected fault and transition the system to a safe state within the fault tolerant time interval (FTTI).", "pass_fail_criteria": "Fault detected; safe state achieved within FTTI; diagnostic trouble code (DTC) is logged.", "equipment": ["CANoe/Vector Tool", "Debugger", "Fault Injection Hardware"], "standard_reference": "ISO 26262"},
    "ip67 ingress test": {"purpose": "To validate the enclosure's sealing against dust and water immersion.", "requirement": "The enclosure must meet the IP67 rating as per IEC 60529, preventing ingress of dust and water when submerged at 1m for 30 mins.", "pass_fail_criteria": "No visible water ingress inside the enclosure after the test; device remains functional.", "equipment": ["Dust Chamber", "Immersion Tank", "Leak Detector"], "standard_reference": "IEC 60529 / ISO 20653"},
    "cybersecurity penetration test": {"purpose": "To identify and exploit vulnerabilities in the device's external interfaces (e.g., CAN, Bluetooth, Wi-Fi).", "requirement": "The device must resist defined attack vectors without allowing unauthorized access, modification of safety-critical data, or denial of service.", "pass_fail_criteria": "Attack vectors are successfully mitigated; no critical vulnerabilities are exploitable.", "equipment": ["CANoe/Vector Tool with Security Manager", "Wi-Fi/BT Hacking Tools (e.g., Kali Linux)", "Custom Fuzzing Scripts"], "standard_reference": "ISO/SAE 21434"},
}

# === MODIFICATION: Massively Expanded Component Database ===
COMPONENT_KNOWLEDGE_BASE = {
    # Regulators
    "lm7805": {"manufacturer": "Texas Instruments", "function": "Positive Voltage Regulator", "type": "Linear Regulator", "output_voltage": "5V", "input_voltage": "7V to 35V", "output_current": "1A", "package": "TO-220", "package_type": "Through-Hole", "certifications": "Industrial"},
    "lm1117": {"manufacturer": "ON Semiconductor", "function": "Low Dropout Positive Voltage Regulator", "type": "LDO Regulator", "output_voltage": "3.3V (Adjustable)", "dropout_voltage": "1.2V at 800mA", "output_current": "800mA", "package": "SOT-223", "package_type": "SMD", "certifications": "Industrial"},
    "lm2596": {"manufacturer": "Texas Instruments", "function": "Step-Down Voltage Regulator", "type": "Switching Regulator", "output_voltage": "1.2V to 37V (Adjustable)", "input_voltage": "4.5V to 40V", "output_current": "3A", "package": "TO-263 (D2PAK)", "package_type": "SMD", "certifications": "Industrial"},
    
    # MOSFETs
    "irfz44n": {"manufacturer": "Infineon", "function": "N-Channel Power MOSFET", "type": "MOSFET", "drain_source_voltage_vdss": "55V", "continuous_drain_current_id": "49A", "on_resistance_rds_on": "17.5 mOhm @ 10V", "package": "TO-220AB", "package_type": "Through-Hole", "certifications": "Industrial"},
    "irf9540n": {"manufacturer": "Vishay", "function": "P-Channel Power MOSFET", "type": "MOSFET", "drain_source_voltage_vdss": "-100V", "continuous_drain_current_id": "-23A", "on_resistance_rds_on": "117 mOhm @ -10V", "package": "TO-220AB", "package_type": "Through-Hole", "certifications": "Industrial"},
    "bss138": {"manufacturer": "NXP", "function": "N-Channel Logic Level Enhancement Mode MOSFET", "type": "MOSFET", "drain_source_voltage_vdss": "50V", "continuous_drain_current_id": "220mA", "on_resistance_rds_on": "3.5 Ohm @ 5V", "package": "SOT-23", "package_type": "SMD", "certifications": "AEC-Q101"},

    # ICs
    "bq76952": {"manufacturer": "Texas Instruments", "function": "16-Series Battery Monitor & Protector", "type": "AFE (Analog Front-End)", "operating_voltage": "Up to 80V", "package": "TQFP-48", "package_type": "SMD", "certifications": "AEC-Q100"},
    "tja1051": {"manufacturer": "NXP", "function": "High-speed CAN transceiver", "type": "Transceiver", "operating_voltage": "5V", "package": "SOIC-8", "package_type": "SMD", "certifications": "AEC-Q100"},
    "lm358": {"manufacturer": "Texas Instruments", "function": "Dual General-Purpose Operational Amplifier", "type": "Op-Amp", "supply_voltage": "3V to 32V", "package": "SOIC-8", "package_type": "SMD", "certifications": "Industrial/AEC-Q100 versions available"},
    "stm32f407": {"manufacturer": "STMicroelectronics", "function": "ARM Cortex-M4 Microcontroller", "type": "MCU", "cpu_speed": "168MHz", "flash_memory": "1MB", "ram": "192KB", "package": "LQFP144", "package_type": "SMD", "certifications": "Industrial"},

    # Diodes & Semiconductors
    "1n4007": {"manufacturer": "Multiple", "function": "General Purpose Rectifier Diode", "type": "Diode", "peak_reverse_voltage": "1000V", "average_forward_current": "1A", "package": "DO-41", "package_type": "Through-Hole", "certifications": "Industrial"},
    "1n5819": {"manufacturer": "Multiple", "function": "Schottky Barrier Rectifier", "type": "Schottky Diode", "peak_reverse_voltage": "40V", "average_forward_current": "1A", "package": "DO-41", "package_type": "Through-Hole", "certifications": "Industrial"},
    "us1m": {"manufacturer": "Vishay", "function": "Ultrafast Surface-Mount Rectifier", "type": "Diode", "peak_reverse_voltage": "1000V", "average_forward_current": "1A", "package": "SMA (DO-214AC)", "package_type": "SMD", "certifications": "AEC-Q101"},

    # Switches
    "ts-1187a": {"manufacturer": "XKB", "function": "Tactile Switch", "type": "Switch", "contact_rating": "50mA @ 12VDC", "actuation_force": "160gf", "package": "6x6mm", "package_type": "Through-Hole", "certifications": "N/A"},
}

# === Intelligent Parser (Unchanged) ===
def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}
        match = re.match(r'^(.*?)(?:\s{2,}|:)\s*(PASS|FAIL|PASSED|FAILED|SUCCESS|FAILURE)\s*$', line, re.I)
        if match:
            test_data["TestName"] = match.group(1).strip().replace(':', '')
            result = match.group(2).upper()
            test_data["Result"] = "PASS" if result in ["PASS", "PASSED", "SUCCESS"] else "FAIL"
            extracted_tests.append(test_data)
            continue
        match = re.match(r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$', line, re.I)
        if match:
            test_data["TestName"] = match.group(1).strip()
            test_data["Result"] = "PASS" if "pass" in match.group(2).lower() or "success" in match.group(2).lower() else "FAIL"
            test_data["Actual"] = match.group(3).strip()
            extracted_tests.append(test_data)
            continue
        match = re.match(r'^\s*status\s*:\s*(pass|fail|passed|failed)\s*$', line, re.I)
        if match and i > 0:
            prev_line_match = re.match(r'^\s*test\s*(?:case|name)?\s*:\s*(.+)$', lines[i-1].strip(), re.I)
            if prev_line_match:
                test_data["TestName"] = prev_line_match.group(1).strip()
                result = match.group(1).upper()
                test_data["Result"] = "PASS" if result.startswith("PASS") else "FAIL"
                extracted_tests.append(test_data)
                continue
    for test in extracted_tests:
        test_name_lower = test["TestName"].lower()
        for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
            if keyword in test_name_lower:
                test["Standard"] = standard
                break
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        content = ""
        if uploaded_file.name.lower().endswith('.csv'):
            return pd.read_csv(uploaded_file, on_bad_lines='skip').to_dict(orient="records")
        elif uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(uploaded_file).to_dict(orient="records")
        elif uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                content = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif uploaded_file.type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"):
            doc = docx.Document(uploaded_file)
            content = "\n".join(p.text for p in doc.paragraphs if p.text)
        else:
            st.error(f"Unsupported file type: {uploaded_file.type}. Please upload PDF, DOCX, XLSX, or CSV.")
            return []
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing the file: {e}")
        return []

# === Sidebar Navigation ===
option = st.sidebar.radio("Navigation Menu", ("Test Report Verification", "Test Requirement Generation", "Component Datasheet Lookup", "Compliance Dashboard"))
st.sidebar.info("An integrated tool for automotive compliance verification. Upload reports, generate test plans, and look up component data.")

# === Module: Test Report Verification (Unchanged) ===
if option == "Test Report Verification":
    st.subheader("Automated Test Report Verification")
    st.caption("Upload any automotive test report (PDF, DOCX, XLSX, CSV). The system will automatically parse results, check against standards, and classify outcomes.")
    uploaded_file = st.file_uploader("Upload a test report", type=["pdf", "docx", "xlsx", "csv"], help="Drag and drop your report file here.")
    if uploaded_file:
        parsed = parse_report(uploaded_file)
        if parsed:
            st.session_state.reports_verified += 1
            failed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "FAIL"]
            passed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "PASS"]
            total_tests = len(failed_tests) + len(passed_tests)
            if total_tests > 0:
                pass_rate = (len(passed_tests) / total_tests) * 100
                st.session_state.last_pass_rate = f"{pass_rate:.1f}%"
            st.metric("Compliance Pass Rate", st.session_state.last_pass_rate, delta=f"{len(failed_tests)} Failures", delta_color="inverse")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h4 style='color:var(--pass);'>✅ {len(passed_tests)} Passed Test Cases</h4>", unsafe_allow_html=True)
                for t in passed_tests:
                    st.markdown(f"<div class='card card-pass'><b>Test:</b> {t.get('TestName', 'N/A')}<br><b>Standard:</b> {t.get('Standard', 'N/A')}<br><b>Result:</b> <span class='result-pass'>PASS</span></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h4 style='color:var(--fail);'>🔴 {len(failed_tests)} FAILED Test Cases</h4>", unsafe_allow_html=True)
                for t in failed_tests:
                    st.markdown(f"<div class='card card-fail'><b>Test:</b> {t.get('TestName', 'N/A')}<br><b>Standard:</b> {t.get('Standard', 'N/A')}<br><b>Result:</b> <span class='result-fail'>FAIL</span></div>", unsafe_allow_html=True)
        else:
            st.warning("No recognizable test data was extracted. The document may be image-based or have a non-standard format.")

# === Module: Test Requirement Generation (Unchanged) ===
elif option == "Test Requirement Generation":
    st.subheader("Formal Test Requirement Generator")
    st.caption("Describe the tests you need, one per line. The system will generate formal requirements based on its automotive knowledge base.")
    default_cases = "Over-voltage protection test\nIP67 ingress test\nFunctional safety mechanism check for BMS\nCybersecurity penetration test for TCU"
    text = st.text_area("Enter test descriptions (one per line):", default_cases, height=150, help="Be descriptive, e.g., 'CAN bus fault tolerance test'.")
    if st.button("Generate Requirements"):
        test_cases = [l.strip() for l in text.split("\n") if l.strip()]
        if test_cases:
            st.session_state.requirements_generated += len(test_cases)
            st.markdown("### Generated Test Requirements")
            for i, case in enumerate(test_cases):
                found_req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if all(word in case.lower() for word in key.split())), None)
                st.markdown(f"<div class='card card-info'>", unsafe_allow_html=True)
                st.markdown(f"<h5>REQ-{i+1:03d}: {case.title()}</h5>", unsafe_allow_html=True)
                if found_req:
                    st.markdown(f"**Purpose:** {found_req['purpose']}<br>**Requirement:** {found_req['requirement']}<br>**Pass/Fail Criteria:** {found_req['pass_fail_criteria']}<br>**Suggested Equipment:** {', '.join(found_req['equipment'])}<br>**Primary Standard:** {found_req['standard_reference']}", unsafe_allow_html=True)
                else:
                    st.markdown("**Requirement:** The system shall be tested to verify its performance and safety related to this case, adhering to all applicable industry and OEM-specific standards.")
                    q = case.replace(" ", "+")
                    st.markdown(f"**Action:** This test case is not in the knowledge base. [Search Google for '{case} automotive standard'](https://www.google.com/search?q={q}+automotive+test+standard)")
                st.markdown("</div>", unsafe_allow_html=True)

# === MODIFICATION: Component Datasheet Lookup with Enhanced DB & Dynamic Display ===
elif option == "Component Datasheet Lookup":
    st.subheader("Component Datasheet Lookup")
    st.caption("Search the internal database for ICs, regulators, MOSFETs, diodes, and other components (both SMD and leaded).")
    
    # Update placeholder to reflect new components
    part_q = st.text_input("Enter Part Number", placeholder="e.g., LM7805, BSS138, STM32F407...").lower().strip().replace(" ", "")
    
    if st.button("Find Component"):
        # Search logic to find a key that is contained within the user's query
        found_data = None
        found_key = None
        for key, data in COMPONENT_KNOWLEDGE_BASE.items():
            if key in part_q:
                found_key = key
                found_data = data
                break
        
        if found_data:
            st.session_state.found_component = {"part_number": found_key.upper(), **found_data}
        else:
            st.session_state.found_component = {}
            st.warning("Component not in internal database. Use the research links below.")
            if part_q:
                c1, c2, c3, c4 = st.columns(4)
                c1.link_button("Octopart", f"https://octopart.com/search?q={part_q}", use_container_width=True)
                c2.link_button("Digi-Key", f"https://www.digikey.com/en/products/result?s={part_q}", use_container_width=True)
                c3.link_button("Mouser", f"https://www.mouser.com/Search/Refine?Keyword={part_q}", use_container_width=True)
                c4.link_button("Google", f"https://www.google.com/search?q={part_q}+datasheet", use_container_width=True)

    if st.session_state.found_component:
        st.markdown("---")
        d = st.session_state.found_component
        
        # Dynamic Spec Sheet Generation
        html_string = f"<div class='spec-sheet'><h4>Datasheet: {d.get('part_number', 'N/A')}</h4>"
        
        # Define the order of keys for a more organized display
        display_order = ['manufacturer', 'function', 'type', 'package_type', 'package', 'certifications']
        # Dynamically add the rest of the keys
        all_keys = list(d.keys())
        remaining_keys = [k for k in all_keys if k not in display_order and k != 'part_number']
        
        # Construct the full display order
        full_display_order = display_order + sorted(remaining_keys)

        for key in full_display_order:
            if key in d and key != 'part_number':
                # Format the key for display (replace underscores, capitalize)
                display_key = key.replace('_', ' ').title()
                html_string += f'<div class="spec-item"><span class="spec-key">{display_key}</span> <span class="spec-value">{d[key]}</span></div>'

        html_string += "</div>"
        st.markdown(html_string, unsafe_allow_html=True)

# === Module: Dashboard (Unchanged) ===
else:
    st.subheader("Session Compliance Dashboard")
    st.caption("A high-level overview of verification activities performed in this session.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified This Session", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Last Report Pass Rate", st.session_state.last_pass_rate)
