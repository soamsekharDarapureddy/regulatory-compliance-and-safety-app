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
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# === Advanced CSS for Styling ===
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
        "reports_verified": 0, "requirements_generated": 0, "found_component": {}, "last_pass_rate": "N/A"
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === MODIFICATION: Refined Header with Logo and New Title ===
logo_col, title_col = st.columns([1, 4])
with logo_col:
    logo_path = "people_tech_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.error("Logo file not found. Ensure 'people_tech_logo.png' is present.")
with title_col:
    st.markdown("""
        <div style="padding-top: 10px;">
          <h1 style="color:var(--accent); font-size:2.8em; margin:0; line-height:1.1;">Regulatory Compliance and Safety Verification Tool</h1>
        </div>
    """, unsafe_allow_html=True)
st.markdown("---")

# === KNOWLEDGE BASES (Unchanged) ===
KEYWORD_TO_STANDARD_MAP = {
    "safety": "ISO 26262", "asil": "ISO 26262", "fusa": "ISO 26262", "cybersecurity": "ISO/SAE 21434", "tara": "ISO/SAE 21434",
    "penetration test": "ISO/SAE 21434", "ip rating": "IEC 60529", "ingress protection": "IEC 60529", "short circuit": "AIS-156 / IEC 62133",
    "overcharge": "AIS-156 / ISO 12405-4", "over-discharge": "AIS-156 / ISO 12405-4", "vibration": "IEC 60068-2-6 / AIS-048",
    "emc": "IEC 61000 / ECE R10", "environmental": "ISO 16750", "can bus": "ISO 11898", "diagnostics": "ISO 14229 (UDS)",
    "autosar": "AUTOSAR Standard", "aspice": "Automotive SPICE (ISO/IEC 330xx)", "misra": "MISRA C/C++ Guidelines"
}

TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage protection": {"purpose": "To verify the device can withstand voltage levels exceeding its rating.", "requirement": "DUT must survive a specified over-voltage condition without damage or creating a safety hazard.", "standard_reference": "ISO 16750-2"},
    "short circuit protection": {"purpose": "To ensure the device can safely handle an external short circuit.", "requirement": "DUT shall safely interrupt a short-circuit without fire or explosion.", "standard_reference": "AIS-156 / IEC 62133"},
    "functional safety mechanism": {"purpose": "To verify that a specific safety mechanism (e.g., watchdog) operates correctly.", "requirement": "The safety mechanism must detect the injected fault and transition the system to a safe state within the FTTI.", "standard_reference": "ISO 26262"},
    "ip67 ingress test": {"purpose": "To validate the enclosure's sealing against dust and water.", "requirement": "The enclosure must meet IP67 rating (1m submersion for 30 mins) with no water ingress.", "standard_reference": "IEC 60529 / ISO 20653"},
    "cybersecurity penetration test": {"purpose": "To identify vulnerabilities in the device's external interfaces.", "requirement": "The device must resist defined attack vectors without allowing unauthorized access or modification of critical data.", "standard_reference": "ISO/SAE 21434"},
}

COMPONENT_KNOWLEDGE_BASE = {
    # --- VEHICLE CONTROL UNIT (VCU) ---
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit MCU", "manufacturer": "STMicroelectronics", "type": "Microcontroller", "package": "LQFP-100", "package_type": "SMD", "certifications": "AEC-Q100"},
    "tja1051t": {"subsystem": "VCU", "part_name": "High-speed CAN Transceiver", "manufacturer": "NXP", "type": "Transceiver", "package": "SOIC-8", "package_type": "SMD", "certifications": "AEC-Q100"},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V Low Dropout Voltage Regulator", "manufacturer": "Infineon", "type": "LDO Regulator", "output_voltage": "5V", "output_current": "400mA", "package": "DSO-14", "package_type": "SMD", "certifications": "AEC-Q100"},

    # --- MOTOR CONTROLLER ---
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "Smart Power Module (SPM)", "manufacturer": "ON Semiconductor", "type": "IGBT Module", "voltage_rating": "600V", "current_rating": "30A", "package": "SPM27-FA", "package_type": "Through-Hole", "certifications": "Industrial"},
    "l6390d": {"subsystem": "Motor Controller", "part_name": "High-voltage Gate Driver", "manufacturer": "STMicroelectronics", "type": "Gate Driver", "operating_voltage": "Up to 600V", "package": "SOIC-16", "package_type": "SMD", "certifications": "Industrial"},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Current Sense Shunt Resistor", "manufacturer": "Vishay", "type": "Resistor", "resistance": "10 mOhm", "tolerance": "1%", "power_rating": "1W", "package": "2512", "package_type": "SMD", "certifications": "AEC-Q200"},
    "mkl-10uf-100v": {"subsystem": "Motor Controller", "part_name": "Metallized Polyester Film Capacitor", "manufacturer": "WIMA", "type": "Film Capacitor", "capacitance": "10 µF", "voltage_rating": "100V", "package": "Radial", "package_type": "Through-Hole", "certifications": "Industrial"},

    # --- INSTRUMENT CLUSTER ---
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "32-bit MCU with Graphics", "manufacturer": "Spansion (Cypress)", "type": "Microcontroller", "package": "LQFP-120", "package_type": "SMD", "certifications": "AEC-Q100"},
    "is31fl3236": {"subsystem": "Instrument Cluster", "part_name": "36-Channel LED Driver", "manufacturer": "ISSI", "type": "LED Driver", "package": "QFN-48", "package_type": "SMD", "certifications": "AEC-Q100"},
    "ac0603fr-0710kl": {"subsystem": "Instrument Cluster", "part_name": "Thick Film Chip Resistor", "manufacturer": "Yageo", "type": "Resistor", "resistance": "10 kOhm", "tolerance": "1%", "power_rating": "0.1W", "package": "0603", "package_type": "SMD", "certifications": "AEC-Q200"},
    "cc0805krx7r9bb104": {"subsystem": "Instrument Cluster", "part_name": "Multilayer Ceramic Capacitor (MLCC)", "manufacturer": "Yageo", "type": "MLCC Capacitor", "capacitance": "100 nF (0.1 µF)", "voltage_rating": "50V", "dielectric": "X7R", "package": "0805", "package_type": "SMD", "certifications": "AEC-Q200"},

    # --- CHARGER & DC-DC CONVERTER ---
    "uc3843bd1g": {"subsystem": "Charger/DC-DC", "part_name": "Current-Mode PWM Controller", "manufacturer": "ON Semiconductor", "type": "PWM Controller IC", "package": "SOIC-8", "package_type": "SMD", "certifications": "AEC-Q100"},
    "irfr3709z": {"subsystem": "Charger/DC-DC", "part_name": "N-Channel Power MOSFET", "manufacturer": "Infineon", "type": "MOSFET", "drain_source_voltage_vdss": "30V", "on_resistance_rds_on": "6.5 mOhm", "package": "DPAK", "package_type": "SMD", "certifications": "AEC-Q101"},
    "eeh-azt1v471": {"subsystem": "Charger/DC-DC", "part_name": "Hybrid Polymer Aluminum Electrolytic Capacitor", "manufacturer": "Panasonic", "type": "Electrolytic Capacitor", "capacitance": "470 µF", "voltage_rating": "35V", "esr": "20 mOhm", "package": "Radial Can", "package_type": "SMD", "certifications": "AEC-Q200"},
}

# === Core Functions (Unchanged) ===
def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        match = re.match(r'^(.*?)(?:\s{2,}|:)\s*(PASS|FAIL|PASSED|FAILED|SUCCESS|FAILURE)\s*$', line, re.I)
        if match:
            test_data = {"TestName": match.group(1).strip().replace(':', ''), "Result": "PASS" if match.group(2).upper() in ["PASS", "PASSED", "SUCCESS"] else "FAIL"}
            for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
                if keyword in test_data["TestName"].lower():
                    test_data["Standard"] = standard
                    break
            extracted_tests.append(test_data)
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            return pd.read_csv(uploaded_file, on_bad_lines='skip').to_dict(orient="records")
        elif uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(uploaded_file).to_dict(orient="records")
        content = ""
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf: content = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif uploaded_file.type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"):
            doc = docx.Document(uploaded_file); content = "\n".join(p.text for p in doc.paragraphs if p.text)
        else:
            st.error(f"Unsupported text file type: {uploaded_file.type}"); return []
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing the file: {e}"); return []

# === Sidebar & Main App Logic ===
option = st.sidebar.radio("Navigation Menu", ("Test Report Verification", "Test Requirement Generation", "E-Bike Component Datasheet Lookup", "Compliance Dashboard"))
st.sidebar.info("An integrated tool for automotive compliance verification.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Automated Test Report Verification")
    st.caption("Upload any automotive test report (PDF, DOCX, XLSX, CSV). The system parses results and classifies outcomes.")
    uploaded_file = st.file_uploader("Upload a test report", type=["pdf", "docx", "xlsx", "csv"], help="Drag and drop your DVP&R or test report file here.")
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            failed_tests = [t for t in parsed_data if str(t.get("Result", "")).upper() == "FAIL"]
            passed_tests = [t for t in parsed_data if str(t.get("Result", "")).upper() == "PASS"]
            total_tests = len(failed_tests) + len(passed_tests)
            if total_tests > 0: st.session_state.last_pass_rate = f"{(len(passed_tests) / total_tests) * 100:.1f}%"
            st.metric("Compliance Pass Rate", st.session_state.last_pass_rate, delta=f"{len(failed_tests)} Failures", delta_color="inverse")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h4 style='color:var(--pass);'>✅ {len(passed_tests)} Passed Cases</h4>", unsafe_allow_html=True)
                for t in passed_tests: st.markdown(f"<div class='card card-pass'><b>Test:</b> {t.get('TestName', 'N/A')}<br><b>Standard:</b> {t.get('Standard', 'N/A')}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h4 style='color:var(--fail);'>🔴 {len(failed_tests)} FAILED Cases</h4>", unsafe_allow_html=True)
                for t in failed_tests: st.markdown(f"<div class='card card-fail'><b>Test:</b> {t.get('TestName', 'N/A')}<br><b>Standard:</b> {t.get('Standard', 'N/A')}</div>", unsafe_allow_html=True)
        else:
            st.warning("No recognizable test data was extracted. The document may be image-based or have a non-standard format.")

# --- Test Requirement Generation Module ---
elif option == "Test Requirement Generation":
    st.subheader("Formal Test Requirement Generator")
    st.caption("Describe needed tests. The system will generate formal requirements from its automotive knowledge base.")
    default_cases = "Over-voltage protection test\nIP67 ingress test for VCU\nMotor controller functional safety check"
    text = st.text_area("Enter test descriptions (one per line):", default_cases, height=120)
    if st.button("Generate Requirements"):
        test_cases = [l.strip() for l in text.split("\n") if l.strip()]
        if test_cases:
            st.session_state.requirements_generated += len(test_cases)
            st.markdown("### Generated Test Requirements")
            for i, case in enumerate(test_cases):
                found_req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if all(word in case.lower() for word in key.split())), None)
                st.markdown(f"<div class='card card-info'><h5>REQ-{i+1:03d}: {case.title()}</h5>", unsafe_allow_html=True)
                if found_req:
                    st.markdown(f"**Purpose:** {found_req['purpose']}<br>**Requirement:** {found_req['requirement']}<br>**Standard:** {found_req['standard_reference']}", unsafe_allow_html=True)
                else:
                    st.markdown("**Requirement:** The system shall be tested to verify performance and safety for this case, adhering to all applicable standards.")
                st.markdown("</div>", unsafe_allow_html=True)

# --- E-Bike Component Datasheet Lookup Module ---
elif option == "E-Bike Component Datasheet Lookup":
    st.subheader("E-Bike Component Datasheet Lookup")
    st.caption("Search the database for automotive-grade components used in VCUs, motor controllers, clusters, and chargers.")
    part_q = st.text_input("Enter Part Number", placeholder="e.g., SPC560P50L3, WSLP2512R0100FE, EEH-AZT1V471...").lower().strip().replace(" ", "")
    
    if st.button("Find Component", use_container_width=True):
        found_data = next(({"part_number": key.upper(), **data} for key, data in COMPONENT_KNOWLEDGE_BASE.items() if key in part_q), None)
        st.session_state.found_component = found_data if found_data else {}
        if not found_data:
            st.warning("Component not in internal database. Use the research links below.")
            if part_q:
                c1, c2, c3 = st.columns(3)
                c1.link_button("Octopart", f"https://octopart.com/search?q={part_q}", use_container_width=True)
                c2.link_button("Digi-Key", f"https://www.digikey.com/en/products/result?s={part_q}", use_container_width=True)
                c3.link_button("Google", f"https://www.google.com/search?q={part_q}+datasheet", use_container_width=True)

    if st.session_state.found_component:
        st.markdown("---")
        d = st.session_state.found_component
        html_string = f"<div class='spec-sheet'><h4>Datasheet: {d.get('part_name', 'N/A')} ({d.get('part_number', '')})</h4>"
        display_order = ['subsystem', 'manufacturer', 'type', 'package_type', 'package', 'certifications']
        remaining_keys = [k for k in d.keys() if k not in display_order and k not in ['part_number', 'part_name']]
        for key in display_order + sorted(remaining_keys):
            if key in d: html_string += f'<div class="spec-item"><span class="spec-key">{key.replace("_", " ").title()}</span> <span class="spec-value">{d[key]}</span></div>'
        html_string += "</div>"
        st.markdown(html_string, unsafe_allow_html=True)

# --- Dashboard Module ---
else:
    st.subheader("Session Compliance Dashboard")
    st.caption("A high-level overview of verification activities performed in this session.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Last Report Pass Rate", st.session_state.last_pass_rate)

