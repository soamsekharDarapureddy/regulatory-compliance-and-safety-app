# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os
import base64

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
.main .block-container {
    padding-top: 2rem;
}
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

# === FINAL HEADER with visual adjustments ===
def get_image_as_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

logo_base64 = get_image_as_base64("people_tech_logo.png")

if logo_base64:
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 100px; margin-right: 25px;"/>
            <div>
                <h1 style="color:#0056b3; margin: 0; font-size: 2.5em; line-height: 1.1;">Regulatory Compliance</h1>
                <h2 style="color:#0056b3; margin: 0; font-size: 1.6em; line-height: 1.1;">& Safety Verification Tool</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("Logo file 'people_tech_logo.png' not found.")
    st.title("Regulatory Compliance & Safety Verification Tool")


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

# --- DEFINITIVE, FULLY RESTORED AND EXPANDED COMPONENT DATABASE ---
COMPONENT_KNOWLEDGE_BASE = {
    # Original E-Bike Systems Components
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit MCU", "manufacturer": "STMicroelectronics", "certifications": "AEC-Q100"},
    "tja1051t": {"subsystem": "VCU", "part_name": "High-speed CAN Transceiver", "manufacturer": "NXP", "certifications": "AEC-Q100"},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V LDO Regulator", "manufacturer": "Infineon", "certifications": "AEC-Q100"},
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "SPM IGBT Module", "manufacturer": "ON Semi", "voltage": "600V"},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Current Sense Resistor", "manufacturer": "Vishay", "certifications": "AEC-Q200"},
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "MCU with Graphics", "manufacturer": "Spansion (Cypress)", "certifications": "AEC-Q100"},
    "uc3843bd1g": {"subsystem": "Charger/DC-DC", "part_name": "PWM Controller", "manufacturer": "ON Semi", "certifications": "AEC-Q100"},
    "eeh-azt1v471": {"subsystem": "Charger/DC-DC", "part_name": "Hybrid Polymer Capacitor", "manufacturer": "Panasonic", "certifications": "AEC-Q200"},
    "bq76952": {"subsystem": "BMS", "part_name": "16-Series Battery Monitor", "manufacturer": "Texas Instruments", "voltage": "Up to 80V"},
    
    # Original General Purpose Components
    "lm7805": {"subsystem": "General", "part_name": "5V Regulator", "manufacturer": "TI"},
    "irfz44n": {"subsystem": "General", "part_name": "N-Channel MOSFET", "manufacturer": "Infineon"},
    "stm32f407": {"subsystem": "General", "part_name": "ARM Cortex-M4 MCU", "manufacturer": "STMicroelectronics"},
    "1n4007": {"subsystem": "General", "part_name": "Rectifier Diode", "manufacturer": "Multiple"},
    "irfb4110": {"manufacturer": "Infineon", "function": "N‑MOSFET", "voltage": "100V", "current": "180A"},

    # New Components from ALS_2.0_BOM_12Nov24.xlsx
    "grt188c81a106me13d": {"subsystem": "ALS Board", "part_name": "10uF Capacitor", "manufacturer": "Murata", "footprint": "C0603"},
    "gcm155l81e104ke02d": {"subsystem": "ALS Board", "part_name": "0.1uF Capacitor", "manufacturer": "Samsung", "footprint": "C0402"},
    "5019530507": {"subsystem": "ALS Board", "part_name": "5-Pin Header", "manufacturer": "Molex"},
    "rt0603fre0710rl": {"subsystem": "ALS Board", "part_name": "10 Ohm Resistor", "manufacturer": "YAGEO", "footprint": "R0603"},
    "veml6031x00": {"subsystem": "ALS Board", "part_name": "Ambient Light Sensor", "manufacturer": "Vishay"},

    # New Components from VIC-Assembly-Module-0127000_1.0.4.pdf
    "01270019-00": {"subsystem": "VIC Module", "part_name": "ANTENNA GPS", "manufacturer": "Unknown"},
    "01270020-00": {"subsystem": "VIC Module", "part_name": "ANTENNA WIFI", "manufacturer": "Unknown"},
    "01270021-00": {"subsystem": "VIC Module", "part_name": "ANTENNA LTE", "manufacturer": "Unknown"},
    "p0024-03": {"subsystem": "VIC Module", "part_name": "PCBA BOARD", "manufacturer": "Unknown"},
    "01270018-00": {"subsystem": "VIC Module", "part_name": "SENSOR ALS-PCBA", "manufacturer": "Unknown"},
    "01270010-02": {"subsystem": "VIC Module", "part_name": "TFT LCD WITH COVER GLASS", "manufacturer": "Unknown"},
}


def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}
        
        patterns = [
            r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$',
            r'^(.*?)\s*-->\s*(.+)$',
            r'^\d+:\s*([A-Z_]+):\s*"([A-Z]+)"$',
            r'^(.+?)\s+is\s+(success|failure|passed|failed)$',
            r'^(.+?)\s+(Failed|Passed)$',
        ]
        
        match = re.match(patterns[0], line, re.I)
        if match:
            test_data["TestName"] = match.group(1).strip()
            test_data["Result"] = "PASS" if match.group(2).lower() in ["passed", "success"] else "FAIL"
            test_data["Actual"] = match.group(3).strip()
        else:
            match = re.match(patterns[1], line, re.I)
            if match:
                test_data["TestName"] = match.group(1).strip()
                result_str = match.group(2).lower()
                if "passed" in result_str or "success" in result_str: test_data["Result"] = "PASS"
                elif "failed" in result_str: test_data["Result"] = "FAIL"
                else: test_data["Result"] = "INFO"
                test_data["Actual"] = match.group(2).strip()
            else:
                match = re.match(patterns[2], line)
                if match:
                    test_data["TestName"] = match.group(1).strip().replace("_", " ")
                    result = match.group(2).strip()
                    test_data["Result"] = result if result in ["PASS", "FAIL"] else "NA"
                else:
                    match = re.match(patterns[3], line, re.I)
                    if match:
                        test_data["TestName"] = match.group(1).strip()
                        test_data["Result"] = "PASS" if match.group(2).lower() in ["success", "passed"] else "FAIL"
                    else:
                        match = re.match(patterns, line, re.I)
                        if match:
                            test_data["TestName"] = match.group(1).strip()
                            test_data["Result"] = "PASS" if match.group(2).lower() == "passed" else "FAIL"
                        else:
                            continue
                            
        test_name_lower = test_data["TestName"].lower()
        for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
            if keyword in test_name_lower:
                test_data["Standard"] = standard
                break
        extracted_tests.append(test_data)
                
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        file_extension = os.path.splitext(uploaded_file.name.lower())[1]

        if file_extension in ['.csv', '.xlsx']:
            df = pd.read_csv(uploaded_file) if file_extension == '.csv' else pd.read_excel(uploaded_file)
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            rename_map = {
                'test': 'TestName', 'standard': 'Standard', 'expected': 'Expected',
                'actual': 'Actual', 'result': 'Result', 'description': 'Description',
                'part': 'TestName', 'manufacturer pn': 'Actual'
            }
            df.rename(columns=rename_map, inplace=True)
            return df.to_dict('records')

        elif file_extension == '.pdf':
             with pdfplumber.open(uploaded_file) as pdf:
                content = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())
        else: # Treat as plain text
             content = uploaded_file.getvalue().decode('utf-8', errors='ignore')

        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing the file: {e}")
        return []

def display_test_card(test_case, color):
    details = f"<b>🧪 Test:</b> {test_case.get('TestName', 'N/A')}<br>"
    display_fields = {
        'Standard': '📘 Standard', 'Expected': '🎯 Expected', 'Actual': '📌 Actual', 'Description': '💬 Description'
    }
    for key, label in display_fields.items():
        value = test_case.get(key)
        if value and str(value).strip() and pd.notna(value) and str(value).lower() not in ['—', 'nan']:
            details += f"<b>{label}:</b> {value}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details}</div>", unsafe_allow_html=True)


# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Test Requirement Generation", "Component Information", "Dashboard & Analytics"))
st.sidebar.info("This tool helps verify compliance reports, generate test requirements, and manage component data.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload text or structured reports (PDF, TXT, CSV, XLSX). The parser extracts and displays all relevant data.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv", "txt", "log"])
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            
            failed_tests = [t for t in parsed_data if "FAIL" in str(t.get("Result", "")).upper()]
            passed_tests = [t for t in parsed_data if "PASS" in str(t.get("Result", "")).upper()]
            other_tests = [t for t in parsed_data if not ("PASS" in str(t.get("Result", "")).upper() or "FAIL" in str(t.get("Result", "")).upper())]

            st.markdown(f"### Found {len(passed_tests)} Passed, {len(failed_tests)} Failed, and {len(other_tests)} Other items.")

            if passed_tests:
                with st.expander("✅ Passed Cases", expanded=True):
                    for t in passed_tests:
                        display_test_card(t, '#1e9f50')
            
            if failed_tests:
                with st.expander("🔴 Failed Cases", expanded=True):
                    for t in failed_tests:
                        display_test_card(t, '#c43a31')
            
            if other_tests:
                with st.expander("ℹ️ Other/Informational Items", expanded=False):
                    for t in other_tests:
                        display_test_card(t, '#808080')
        else:
            st.warning("No recognizable data was extracted. Please check the file content and format.")

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
            st.markdown("#### Generated Requirements")
            for i, case in enumerate(test_cases):
                found_req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if key.replace(" test", "") in case.lower()), None)
                req_html = f"<div class='card' style='border-left-color:#7c3aed;'><b>Test Case:</b> {case.title()}<br><b>Req ID:</b> REQ_{i+1:03d}<br>"
                if found_req:
                    req_html += f"<b>Description:</b> {found_req['requirement']}<br><b>Equipment:</b> {', '.join(found_req['equipment'])}"
                else:
                    req_html += "<b>Description:</b> Generic requirement - system must handle this case.<br><b>Equipment:</b> To be determined."
                st.markdown(req_html + "</div>", unsafe_allow_html=True)

elif option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts in the internal database or use web search shortcuts.")
    
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., irfz44n, bq76952").lower().strip()
    if st.button("Find Component"):
        found_key = next((k for k in COMPONENT_KNOWLEDGE_BASE if k in part_q), None)
        if found_key:
            st.session_state.found_component = {"part_number": found_key, **COMPONENT_KNOWLEDGE_BASE[found_key]}
            st.success(f"Found: {found_key.upper()}. Details populated below.")
        else:
            st.session_state.found_component = {}
            st.warning("Not in internal DB. Use research links:")
            if part_q:
                c1, c2, c3 = st.columns(3)
                c1.link_button("Octopart", f"https://octopart.com/search?q={part_q}")
                c2.link_button("Digi-Key", f"https://www.digikey.com/en/products/result?s={part_q}")
                c3.link_button("Google", f"https://www.google.com/search?q={part_q}+datasheet")
                
    st.markdown("---")
    d = st.session_state.get('found_component', {})
    with st.form("component_form", clear_on_submit=True):
        st.markdown("### Add Component to Project Database")
        pn = st.text_input("Part Number", value=d.get("part_number", ""))
        mfg = st.text_input("Manufacturer", value=d.get("manufacturer", ""))
        func = st.text_input("Function / Part Name", value=d.get("part_name", d.get("function", "")))
        notes = st.text_area("Notes (e.g., Certifications, Subsystem, Voltage)", value=d.get("certifications", d.get("subsystem", "")))
        
        if st.form_submit_button("Add Component"):
            if pn:
                new_row = pd.DataFrame([{"Part Number": pn, "Manufacturer": mfg, "Function": func, "Notes": notes}])
                st.session_state.component_db = pd.concat([st.session_state.component_db, new_row], ignore_index=True)
                st.success(f"Component '{pn}' added to the database.")
                st.session_state.found_component = {}

    if not st.session_state.component_db.empty:
        st.markdown("#### Project Component Database")
        st.dataframe(st.session_state.component_db, use_container_width=True)

else: # Dashboard
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of compliance progress during this session.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in DB", len(st.session_state.component_db))
