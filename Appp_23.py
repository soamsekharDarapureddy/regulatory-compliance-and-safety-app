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
:root { --accent:#0056b3; --panel:#f3f8fc; --shadow:#cfe7ff; }
.card{background:#fff; border-radius:10px; padding:12px 14px; margin-bottom:10px; border-left:8px solid #c9d6e8;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
.result-na{color:#808080; font-weight:700;}
a {text-decoration: none;}
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = {
        "reports_verified": 0, "requirements_generated": 0, "found_component": {}, "component_db": pd.DataFrame()
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === Refined Header ===
logo_col, title_col = st.columns([1, 5])
with logo_col:
    logo_path = "people_tech_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=100)
    else:
        st.markdown("#### PEOPLE_TECH")
with title_col:
    st.markdown("""
        <div style="background:var(--accent); padding:10px 22px; border-radius:14px;">
          <h1 style="color:#fff; font-size:1.8em; margin:0; line-height:1.2;">E-Bike Regulatory Compliance & Safety Checking tool</h1>
          <p style="color:#eaf4ff; margin:0; font-weight:500;">A People TECH Company Solution</p>
        </div>
    """, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# === KNOWLEDGE BASES ===
KEYWORD_TO_STANDARD_MAP = {
    # Connectivity
    "gps": "NMEA 0183 / GNSS Performance Standards", "gnss": "3GPP / GNSS Performance Standards",
    "bluetooth": "Bluetooth Core Specification", "wifi": "IEEE 802.11 Standards",
    "wi-fi": "IEEE 802.11 Standards", "lte": "3GPP LTE Standards", "4g": "3GPP LTE Standards",
    "sim": "ISO/IEC 7816", "can": "ISO 11898", "usb": "USB-IF Standards",
    # Sensors
    "sensor": "AEC-Q104 (Sensors)", "gyro": "AEC-Q104 (Sensors)", "accelero": "AEC-Q104 (Sensors)",
    "magneto": "AEC-Q104 (Sensors)", "temp": "System Thermal Design Spec",
    # Software & Stability
    "touch": "HMI/Driver Interface Spec", "display": "Display Quality Standards", "rgb": "Display Quality Standards",
    "crash": "System Stability/Software Quality Standard", "anr": "System Stability/Software Quality Standard",
    "watchdog": "System Watchdog Functionality Spec", "rtc": "System Real-Time Clock Spec",
    "memory": "Embedded System Memory Management", "modem": "3GPP Modem Interface Standards",
    # E-Bike Specific
    "ip rating": "IEC 60529", "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156 / ISO 12405-4",
    "over-discharge": "AIS-156 / ISO 12405-4", "vibration": "IEC 60068-2-6 / AIS-048",
    "fatigue": "ISO 4210-6", "braking": "EN 15194 / ISO 4210-2", "emc": "IEC 61000 / EN 15194"
}
TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage": {"requirement": "DUT must withstand specified over-voltage without unsafe condition.", "equipment": ["DC Power Supply", "DMM", "Oscilloscope"]},
    "short circuit": {"requirement": "DUT shall safely interrupt short-circuit within time limits.", "equipment": ["High-Current Supply", "Oscilloscope", "Shorting Switch"]},
    "insulation resistance": {"requirement": "Insulation resistance between live parts and chassis must be above minimum.", "equipment": ["Insulation Resistance Tester (Megger)"]},
    "ip rating": {"requirement": "Enclosure must meet declared IP code for dust and water ingress.", "equipment": ["Dust Chamber", "Water Jet Nozzles"]},
    "vibration": {"requirement": "DUT must withstand vibration levels without mechanical failure.", "equipment": ["Shaker Table", "Accelerometer"]},
    "frame fatigue": {"requirement": "Frame must survive specified cyclic loads per ISO 4210.", "equipment": ["Fatigue Test Rig", "Strain Gauges"]},
}
for k, v in list(TEST_CASE_KNOWLEDGE_BASE.items()): TEST_CASE_KNOWLEDGE_BASE[k + " test"] = v

# --- CORRECTION: Fully Restored Component Database ---
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

def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}
        
        # CORRECTED REGEX: Using raw strings (r"...") to handle backslashes correctly.
        match1 = re.match(r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$', line, re.I)
        if match1:
            test_data["TestName"] = match1.group(1).strip()
            result_str = match1.group(2).lower()
            test_data["Result"] = "PASS" if "passed" in result_str or "success" in result_str else "FAIL"
            test_data["Actual"] = match1.group(3).strip()
            extracted_tests.append(test_data)
            continue
            
        match2 = re.match(r'^(.*?)\s*-->\s*(.+)$', line, re.I)
        if match2:
            test_data["TestName"] = match2.group(1).strip()
            result_str = match2.group(2).lower()
            if "passed" in result_str or "success" in result_str:
                test_data["Result"] = "PASS"
            elif "failed" in result_str:
                test_data["Result"] = "FAIL"
            else:
                test_data["Result"] = "INFO"
            test_data["Actual"] = match2.group(2).strip()
            extracted_tests.append(test_data)
            continue
            
        match3 = re.match(r'^\d+:\s*([A-Z_]+):\s*"([A-Z]+)"$', line)
        if match3:
            test_data["TestName"] = match3.group(1).strip()
            result = match3.group(2).strip()
            test_data["Result"] = result if result in ["PASS", "FAIL"] else "NA"
            extracted_tests.append(test_data)
            continue
            
        match4 = re.match(r'^(.+?)\s+is\s+(success|failure|passed|failed)$', line, re.I)
        if match4:
            test_data["TestName"] = match4.group(1).strip()
            result_str = match4.group(2).lower()
            test_data["Result"] = "PASS" if "success" in result_str or "passed" in result_str else "FAIL"
            extracted_tests.append(test_data)
            continue
            
        match5 = re.match(r'^(.+?)\s+(Failed|Passed)$', line, re.I)
        if match5:
            test_data["TestName"] = match5.group(1).strip()
            test_data["Result"] = "PASS" if "passed" in match5.group(2).lower() else "FAIL"
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
            df = pd.read_csv(uploaded_file)
            return df.to_dict(orient="records")
        elif uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages: content += (page.extract_text() or "") + "\n"
        elif uploaded_file.type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"):
            doc = docx.Document(uploaded_file)
            content = "\n".join(p.text for p in doc.paragraphs if p.text)
        elif uploaded_file.type in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"):
            df = pd.read_excel(uploaded_file)
            return df.to_dict(orient="records")
        else:
            st.error(f"Unsupported file type: {uploaded_file.type}")
            return []
        
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing the file: {e}")
        return []

# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Test Requirement Generation", "Component Information", "Dashboard & Analytics"))
st.sidebar.info("This tool helps verify compliance reports, generate test requirements, and manage component data.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload PDF/DOCX/XLSX/CSV reports. The parser extracts tests and groups them by PASS/FAIL status.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv"])
    if uploaded_file:
        parsed = parse_report(uploaded_file)
        if parsed:
            st.session_state.reports_verified += 1
            
            failed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "FAIL"]
            passed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "PASS"]
            other_tests = [t for t in parsed if str(t.get("Result", "")).upper() not in ["PASS", "FAIL"]]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h4 style='color:#1e9f50;'>✅ {len(passed_tests)} Passed Test Case(s)</h4>", unsafe_allow_html=True)
                if passed_tests:
                    for t in passed_tests:
                        st.markdown(
                            f"<div class='card' style='border-left-color:#1e9f50;'>"
                            f"<b>🧪 Test:</b> {t.get('TestName', 'N/A')}<br>"
                            f"<b>📘 Standard:</b> {t.get('Standard', 'N/A')}<br>"
                            f"<b>📊 Result:</b> <span class='result-pass'>PASS</span><br>"
                            f"<b>📌 Actual/Value:</b> {t.get('Actual', 'N/A')}<br>"
                            f"</div>", unsafe_allow_html=True
                        )
                else:
                    st.info("No passed tests were found in the report.")
            
            with col2:
                st.markdown(f"<h4 style='color:#c43a31;'>🔴 {len(failed_tests)} FAILED Test Case(s)</h4>", unsafe_allow_html=True)
                if failed_tests:
                    for t in failed_tests:
                        st.markdown(
                            f"<div class='card' style='border-left-color:#c43a31;'>"
                            f"<b>🧪 Test:</b> {t.get('TestName', 'N/A')}<br>"
                            f"<b>📘 Standard:</b> {t.get('Standard', 'N/A')}<br>"
                            f"<b>📊 Result:</b> <span class='result-fail'>FAIL</span><br>"
                            f"<b>📌 Actual/Value:</b> {t.get('Actual', 'N/A')}<br>"
                            f"</div>", unsafe_allow_html=True
                        )
                else:
                    st.info("No failed tests were found in the report.")
            
            st.markdown("---")
            if other_tests:
                with st.expander(f"ℹ️ View {len(other_tests)} Other/Informational Test Case(s)", expanded=False):
                    for t in other_tests:
                        result_upper = str(t.get('Result', 'NA')).upper()
                        st.markdown(
                            f"<div class='card'>"
                            f"<b>🧪 Test:</b> {t.get('TestName', 'N/A')}<br>"
                            f"<b>📘 Standard:</b> {t.get('Standard', 'N/A')}<br>"
                            f"<b>📊 Result:</b> <span class='result-na'>{result_upper}</span><br>"
                            f"<b>📌 Actual/Value:</b> {t.get('Actual', 'N/A')}<br>"
                            f"</div>", unsafe_allow_html=True
                        )
        else:
            st.warning("No recognizable test data was extracted. Please check the report content and format.")

# --- Other Modules ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Test Requirements", anchor=False)
    st.caption("Enter one test per line to generate formal requirements and equipment lists.")
    default_cases = "ip rating\nshort circuit\nframe fatigue test"
    text = st.text_area("Test cases (one per line)", default_cases, height=120)
    
    if st.button("Generate Requirements"):
        test_cases = [l.strip() for l in text.split("\n") if l.strip()]
        if test_cases:
            st.session_state.requirements_generated += len(test_cases)
            
            reqs = []
            for i, case in enumerate(test_cases):
                found_req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if key.replace(" test", "") in case.lower()), None)
                if found_req:
                    reqs.append({
                        "Test Case": case.title(), "Requirement ID": f"REQ_{i+1:03d}",
                        "Requirement Description": found_req["requirement"], "Required Equipment": ", ".join(found_req["equipment"])
                    })
                else:
                    reqs.append({
                        "Test Case": case.title(), "Requirement ID": f"REQ_{i+1:03d}",
                        "Requirement Description": "Generic requirement: System must handle this case according to relevant industry standards.", 
                        "Required Equipment": "To be determined.",
                        "external_search": case
                    })
            
            st.markdown("#### Generated Requirements")
            for r in reqs:
                st.markdown(f"<div class='card' style='border-left-color:#7c3aed;'>"
                            f"<b>📝 Test Case:</b> {r['Test Case']}<br>"
                            f"<b>🆔 Requirement ID:</b> {r['Requirement ID']}<br>"
                            f"<b>📋 Description:</b> {r['Requirement Description']}<br>"
                            f"<b>🛠️ Required Equipment:</b> {r['Required Equipment']}"
                            f"</div>", unsafe_allow_html=True)
                if "external_search" in r:
                    q = r["external_search"]
                    st.caption(f"Research link for '{q}': [Google](https://www.google.com/search?q={q}+test+standard)")

elif option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts in the internal database or use web search shortcuts.")
    
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., spc560p50l3, irfz44n...").lower().strip()
    if st.button("Find Component"):
        # Search the comprehensive database
        found_key = next((k for k in COMPONENT_KNOWLEDGE_BASE if k in part_q), None)
        if found_key:
            found = COMPONENT_KNOWLEDGE_BASE[found_key]
            st.success(f"Found: {part_q.upper()}. Details populated below.")
            st.session_state.found_component = {"part_number": part_q.upper(), **found}
        else:
            st.session_state.found_component = {}
            st.warning("Not in internal DB. Research with these links:")
            if part_q:
                c1, c2, c3, c4 = st.columns(4)
                c1.link_button("Octopart", f"https://octopart.com/search?q={part_q}")
                c2.link_button("Digi-Key", f"https://www.digikey.com/en/products/result?s={part_q}")
                c3.link_button("Mouser", f"https://www.mouser.com/Search/Refine?Keyword={part_q}")
                c4.link_button("Google", f"https://www.google.com/search?q={part_q}+datasheet")
                
    st.markdown("---")
    
    d = st.session_state.get('found_component', {})
    with st.form("component_form", clear_on_submit=True):
        st.markdown("### Add Component to Database")
        pn = st.text_input("Part Number", value=d.get("part_number", ""))
        mfg = st.text_input("Manufacturer", value=d.get("manufacturer", ""))
        func = st.text_input("Function / Part Name", value=d.get("part_name", d.get("function", "")))
        val1 = st.text_input("Key Spec (e.g., Voltage, Resistance)", value=d.get("output_voltage", d.get("voltage_rating", "")))
        notes = st.text_area("Notes (e.g., certifications, package)", value=d.get("certifications", ""))
        
        if st.form_submit_button("Add Component"):
            if pn:
                new_row = pd.DataFrame([{"Part Number": pn, "Manufacturer": mfg, "Function": func, "Key Spec": val1, "Notes": notes}])
                st.session_state.component_db = pd.concat([st.session_state.component_db, new_row], ignore_index=True)
                st.success(f"Component '{pn}' added to the database.")
                st.session_state.found_component = {}

    if not st.session_state.component_db.empty:
        st.markdown("#### Component Database")
        st.dataframe(st.session_state.component_db, use_container_width=True)

else: # Dashboard
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of compliance progress during this session.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in DB", len(st.session_state.component_db))
