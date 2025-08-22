# app.py
import streamlit as st
import pandas as pd
import pdfplumber
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

# === Refined Header ===
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


# === KNOWLEDGE BASES ===
KEYWORD_TO_STANDARD_MAP = {
    "safety": "ISO 26262", "asil": "ISO 26262", "fusa": "ISO 26262", "cybersecurity": "ISO/SAE 21434", "tara": "ISO/SAE 21434",
    "penetration test": "ISO/SAE 21434", "ip rating": "IEC 60529", "ingress protection": "IEC 60529", "short circuit": "AIS-156 / IEC 62133",
    "overcharge": "AIS-156 / ISO 12405-4", "over-discharge": "AIS-156 / ISO 12405-4", "vibration": "IEC 60068-2-6 / AIS-048",
    "emc": "IEC 61000", "iec 61000": "IEC 61000", "ais-138": "AIS-138", "is 13252": "IS 13252",
    "environmental": "ISO 16750", "can bus": "ISO 11898", "diagnostics": "ISO 14229 (UDS)",
}

TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage protection": {"purpose": "To verify the device can withstand voltage levels exceeding its rating.", "requirement": "DUT must survive a specified over-voltage condition without damage or creating a safety hazard.", "standard_reference": "ISO 16750-2"},
    "short circuit protection": {"purpose": "To ensure the device can safely handle an external short circuit.", "requirement": "DUT shall safely interrupt a short-circuit without fire or explosion.", "standard_reference": "AIS-156 / IEC 62133"},
}

# --- Fully Restored Component Database ---
COMPONENT_KNOWLEDGE_BASE = {
    # --- E-BIKE: VEHICLE CONTROL UNIT (VCU) ---
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit MCU", "manufacturer": "STMicroelectronics", "type": "Microcontroller", "package": "LQFP-100", "package_type": "SMD", "certifications": "AEC-Q100"},
    "tja1051t": {"subsystem": "VCU", "part_name": "High-speed CAN Transceiver", "manufacturer": "NXP", "type": "Transceiver", "package": "SOIC-8", "package_type": "SMD", "certifications": "AEC-Q100"},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V Low Dropout Voltage Regulator", "manufacturer": "Infineon", "type": "LDO Regulator", "output_voltage": "5V", "output_current": "400mA", "package": "DSO-14", "package_type": "SMD", "certifications": "AEC-Q100"},

    # --- E-BIKE: MOTOR CONTROLLER ---
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "Smart Power Module (SPM)", "manufacturer": "ON Semiconductor", "type": "IGBT Module", "voltage_rating": "600V", "current_rating": "30A", "package": "SPM27-FA", "package_type": "Through-Hole", "certifications": "Industrial"},
    "l6390d": {"subsystem": "Motor Controller", "part_name": "High-voltage Gate Driver", "manufacturer": "STMicroelectronics", "type": "Gate Driver", "operating_voltage": "Up to 600V", "package": "SOIC-16", "package_type": "SMD", "certifications": "Industrial"},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Current Sense Shunt Resistor", "manufacturer": "Vishay", "type": "Resistor", "resistance": "10 mOhm", "tolerance": "1%", "power_rating": "1W", "package": "2512", "package_type": "SMD", "certifications": "AEC-Q200"},
    "mkl-10uf-100v": {"subsystem": "Motor Controller", "part_name": "Metallized Polyester Film Capacitor", "manufacturer": "WIMA", "type": "Film Capacitor", "capacitance": "10 µF", "voltage_rating": "100V", "package": "Radial", "package_type": "Through-Hole", "certifications": "Industrial"},

    # --- E-BIKE: INSTRUMENT CLUSTER ---
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "32-bit MCU with Graphics", "manufacturer": "Spansion (Cypress)", "type": "Microcontroller", "package": "LQFP-120", "package_type": "SMD", "certifications": "AEC-Q100"},
    "is31fl3236": {"subsystem": "Instrument Cluster", "part_name": "36-Channel LED Driver", "manufacturer": "ISSI", "type": "LED Driver", "package": "QFN-48", "package_type": "SMD", "certifications": "AEC-Q100"},
    "ac0603fr-0710kl": {"subsystem": "Instrument Cluster", "part_name": "Thick Film Chip Resistor", "manufacturer": "Yageo", "type": "Resistor", "resistance": "10 kOhm", "tolerance": "1%", "power_rating": "0.1W", "package": "0603", "package_type": "SMD", "certifications": "AEC-Q200"},
    "cc0805krx7r9bb104": {"subsystem": "Instrument Cluster", "part_name": "Multilayer Ceramic Capacitor (MLCC)", "manufacturer": "Yageo", "type": "MLCC Capacitor", "capacitance": "100 nF (0.1 µF)", "voltage_rating": "50V", "dielectric": "X7R", "package": "0805", "package_type": "SMD", "certifications": "AEC-Q200"},

    # --- E-BIKE: CHARGER & DC-DC CONVERTER ---
    "uc3843bd1g": {"subsystem": "Charger/DC-DC", "part_name": "Current-Mode PWM Controller", "manufacturer": "ON Semiconductor", "type": "PWM Controller IC", "package": "SOIC-8", "package_type": "SMD", "certifications": "AEC-Q100"},
    "irfr3709z": {"subsystem": "Charger/DC-DC", "part_name": "N-Channel Power MOSFET", "manufacturer": "Infineon", "type": "MOSFET", "drain_source_voltage_vdss": "30V", "on_resistance_rds_on": "6.5 mOhm", "package": "DPAK", "package_type": "SMD", "certifications": "AEC-Q101"},
    "eeh-azt1v471": {"subsystem": "Charger/DC-DC", "part_name": "Hybrid Polymer Aluminum Electrolytic Capacitor", "manufacturer": "Panasonic", "type": "Electrolytic Capacitor", "capacitance": "470 µF", "voltage_rating": "35V", "esr": "20 mOhm", "package": "Radial Can", "package_type": "SMD", "certifications": "AEC-Q200"},
    
    # --- GENERAL-PURPOSE AUTOMOTIVE & INDUSTRIAL COMPONENTS ---
    # Regulators
    "lm7805": {"subsystem": "General", "part_name": "Positive Voltage Regulator", "manufacturer": "Texas Instruments", "type": "Linear Regulator", "output_voltage": "5V", "input_voltage": "7V to 35V", "package": "TO-220", "package_type": "Through-Hole", "certifications": "Industrial"},
    "lm1117": {"subsystem": "General", "part_name": "Low Dropout Positive Voltage Regulator", "manufacturer": "ON Semiconductor", "type": "LDO Regulator", "output_voltage": "3.3V (Adjustable)", "package": "SOT-223", "package_type": "SMD", "certifications": "Industrial"},
    "lm2596": {"subsystem": "General", "part_name": "Step-Down Voltage Regulator", "manufacturer": "Texas Instruments", "type": "Switching Regulator", "output_voltage": "1.2V to 37V", "package": "TO-263", "package_type": "SMD", "certifications": "Industrial"},
    # MOSFETs
    "irfz44n": {"subsystem": "General", "part_name": "N-Channel Power MOSFET", "manufacturer": "Infineon", "type": "MOSFET", "drain_source_voltage_vdss": "55V", "package": "TO-220AB", "package_type": "Through-Hole", "certifications": "Industrial"},
    "bss138": {"subsystem": "General", "part_name": "N-Channel Logic Level MOSFET", "manufacturer": "NXP", "type": "MOSFET", "drain_source_voltage_vdss": "50V", "package": "SOT-23", "package_type": "SMD", "certifications": "AEC-Q101"},
    # ICs
    "lm358": {"subsystem": "General", "part_name": "Dual General-Purpose Op-Amp", "manufacturer": "Texas Instruments", "type": "Op-Amp", "supply_voltage": "3V to 32V", "package": "SOIC-8", "package_type": "SMD", "certifications": "Industrial/AEC-Q100 versions"},
    "stm32f407": {"subsystem": "General", "part_name": "ARM Cortex-M4 MCU", "manufacturer": "STMicroelectronics", "type": "MCU", "flash_memory": "1MB", "package": "LQFP144", "package_type": "SMD", "certifications": "Industrial"},
    # Diodes
    "1n4007": {"subsystem": "General", "part_name": "General Purpose Rectifier Diode", "manufacturer": "Multiple", "type": "Diode", "peak_reverse_voltage": "1000V", "package": "DO-41", "package_type": "Through-Hole", "certifications": "Industrial"},
    "us1m": {"subsystem": "General", "part_name": "Ultrafast Surface-Mount Rectifier", "manufacturer": "Vishay", "type": "Diode", "peak_reverse_voltage": "1000V", "package": "SMA (DO-214AC)", "package_type": "SMD", "certifications": "AEC-Q101"},
}

# === FINAL, CORRECTED PARSER USING PDFPLUMBER'S TABLE EXTRACTION ===
def parse_report(uploaded_file):
    if not uploaded_file:
        return []

    try:
        parsed_data = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # Use extract_tables() which is robust for structured data
                tables = page.extract_tables()
                for table in tables:
                    # Assuming the first row is headers, which we can skip or use
                    for row in table[1:]: # Start from the second row
                        if len(row) >= 4:
                            test_data = {
                                "TestName": row[0] or "N/A",
                                "Standard": row[0] or "N/A", # Often the test name is the standard
                                "Expected": row[1] or "N/A",
                                "Actual": row[2] or "N/A",
                                "Result": str(row[3]).upper() if row[3] else "N/A",
                                "Observations": row[4] if len(row) > 4 else "N/A"
                            }
                            # Clean up newlines that can get stuck in cells
                            for key, value in test_data.items():
                                if isinstance(value, str):
                                    test_data[key] = value.replace('\n', ' ')
                            parsed_data.append(test_data)
        return parsed_data
    except Exception as e:
        st.error(f"An error occurred while parsing the PDF tables: {e}")
        return []


# === Sidebar & Main App Logic ===
option = st.sidebar.radio("Navigation Menu", ("Test Report Verification", "Test Requirement Generation", "E-Bike Component Datasheet Lookup", "Compliance Dashboard"))
st.sidebar.info("An integrated tool for automotive compliance verification.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Automated Test Report Verification")
    st.caption("Upload a PDF test report. The system will extract tabular data and classify outcomes.")
    uploaded_file = st.file_uploader("Upload a test report (PDF with tables)", type=["pdf"], help="This tool is optimized for PDF files containing data in tables.")

    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            failed_tests = [t for t in parsed_data if t.get("Result") == "FAIL"]
            passed_tests = [t for t in parsed_data if t.get("Result") == "PASS"]
            
            total_classified = len(failed_tests) + len(passed_tests)
            if total_classified > 0:
                st.session_state.last_pass_rate = f"{(len(passed_tests) / total_classified) * 100:.1f}%"
            
            st.metric("Compliance Pass Rate (Pass / (Pass+Fail))", st.session_state.last_pass_rate, delta=f"{len(failed_tests)} Failures", delta_color="inverse")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h4 style='color:var(--pass);'>✅ {len(passed_tests)} Passed Cases</h4>", unsafe_allow_html=True)
                for t in passed_tests:
                    st.markdown(f"<div class='card card-pass'>"
                                f"<b>Test:</b> {t.get('TestName', 'N/A')}<br>"
                                f"<b>Expected:</b> {t.get('Expected', 'N/A')}<br>"
                                f"<b>Actual:</b> {t.get('Actual', 'N/A')}"
                                f"</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h4 style='color:var(--fail);'>🔴 {len(failed_tests)} FAILED Cases</h4>", unsafe_allow_html=True)
                for t in failed_tests:
                    st.markdown(f"<div class='card card-fail'>"
                                f"<b>Test:</b> {t.get('TestName', 'N/A')}<br>"
                                f"<b>Expected:</b> {t.get('Expected', 'N/A')}<br>"
                                f"<b>Actual:</b> {t.get('Actual', 'N/A')}"
                                f"</div>", unsafe_allow_html=True)
        else:
            st.warning("Could not extract any tables from the provided PDF. Please ensure the report contains structured tables.")

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
    part_q = st.text_input("Enter Part Number", placeholder="e.g., SPC560P50L3, WSLP2512R0100FE...").lower().strip().replace(" ", "")
    
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

