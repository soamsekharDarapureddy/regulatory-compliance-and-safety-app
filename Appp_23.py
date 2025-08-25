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
.component-card{background:#f8f9fa; border-left: 8px solid #0056b3; padding: 15px; border-radius: 10px; margin-top: 15px;}
.component-title{color:#0056b3; font-size: 1.5em; font-weight: 600; margin-bottom: 10px;}
.component-detail{font-size: 1.05em; margin-bottom: 5px;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
a {text-decoration: none;}
.main .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = { "reports_verified": 0, "requirements_generated": 0, "found_component": {}, "component_db": pd.DataFrame() }
    for key, value in state_defaults.items():
        if key not in st.session_state: st.session_state[key] = value
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
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 120px; margin-right: 25px;"/>
            <div>
                <h1 style="color:#0056b3; margin: 0; font-size: 2.2em; line-height: 1.0;">Regulatory Compliance</h1>
                <h2 style="color:#0056b3; margin: 0; font-size: 1.4em; line-height: 1.0;">& Safety Verification Tool</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("Logo file 'people_tech_logo.png' not found.")
    st.title("Regulatory Compliance & Safety Verification Tool")

# === KNOWLEDGE BASES ===
KEYWORD_TO_STANDARD_MAP = { "gps": "NMEA 0183", "gnss": "3GPP", "bluetooth": "Bluetooth Core Spec", "wifi": "IEEE 802.11", "lte": "3GPP LTE", "can": "ISO 11898", "sensor": "AEC-Q104", "ip rating": "IEC 60529", "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156", "vibration": "IEC 60068-2-6" }
TEST_CASE_KNOWLEDGE_BASE = { "over-voltage": {"requirement": "DUT must withstand over-voltage.", "equipment": ["DC Power Supply", "DMM"]}, "short circuit": {"requirement": "DUT shall safely interrupt short-circuit.", "equipment": ["High-Current Supply", "Oscilloscope"]}, "vibration": {"requirement": "DUT must withstand vibration.", "equipment": ["Shaker Table"]} }

# --- Enriched Component Databases ---
COMPONENT_KNOWLEDGE_BASE = {
    # Key Components with Detailed Specs
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit Automotive Microcontroller", "manufacturer": "STMicroelectronics", "grade": "Automotive", "voltage_min": 3.0, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125},
    "tja1051t": {"subsystem": "VCU", "part_name": "High-speed CAN Transceiver", "manufacturer": "NXP", "grade": "Automotive", "voltage_min": 4.5, "voltage_max": 5.5, "temp_min": -40, "temp_max": 150},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V LDO Regulator", "manufacturer": "Infineon", "grade": "Automotive", "voltage_min": 5.5, "voltage_max": 45, "current_max": 0.45, "temp_min": -40, "temp_max": 150},
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "Motion SPM® 3 IGBT Module", "manufacturer": "onsemi", "grade": "Industrial", "voltage_max": 600, "current_max": 30, "temp_min": -20, "temp_max": 125},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Power Metal Strip® Resistor", "manufacturer": "Vishay", "grade": "Automotive", "temp_min": -65, "temp_max": 170},
    "bq76952": {"subsystem": "BMS", "part_name": "16-Series Battery Monitor", "manufacturer": "Texas Instruments", "grade": "Automotive", "voltage_max": 80},
    "irfz44n": {"subsystem": "General", "part_name": "N-Channel Power MOSFET", "manufacturer": "Infineon", "grade": "Industrial", "voltage_max": 55, "current_max": 49, "temp_min": -55, "temp_max": 175},
    
    # Large list of newly added general components
    "fh28-10s-0.5sh(05)": {"manufacturer": "Hirose Electric Co Ltd", "part_name": "Connector"},
    "gcm155l81e104ke02d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor"},
    "cga3e3x7s1a225k080ae": {"manufacturer": "TDK Corporation", "part_name": "Capacitor"},
    "zldo1117qg33ta": {"manufacturer": "Diodes Incorporated", "part_name": "LDO Regulator"},
    "ap63357qzv-7": {"manufacturer": "Diodes Incorporated", "part_name": "Switching Regulator"},
    "pca9306idcurq1": {"manufacturer": "Texas Instruments", "part_name": "Level Translator"},
    "mcp2518fdt-e/sl": {"manufacturer": "Microchip Technology", "part_name": "CAN Controller"},
    "iso1042bqdwvq1": {"manufacturer": "Texas Instruments", "part_name": "CAN Transceiver"},
    "pesd2canfd27v-tr": {"manufacturer": "Nexperia USA Inc.", "part_name": "ESD Protection"},
    "lt8912b": {"manufacturer": "Lontium", "part_name": "MIPI DSI/CSI-2 Bridge"},
    "sn74lv1t34qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Buffer"},
    "ncp164csnadjt1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator"},
    "20279-001e-03": {"manufacturer": "I-PEX", "part_name": "Connector"},
    "ncv8161asn180t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator"},
    "drtr5v0u2sr-7": {"manufacturer": "Diodes Incorporated", "part_name": "ESD Protection"},
    "ncv8161asn330t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator"},
    "ecmf04-4hswm10y": {"manufacturer": "STMicroelectronics", "part_name": "Common Mode Filter"},
    "nxs0102dc-q100h": {"manufacturer": "Nexperia USA Inc.", "part_name": "Level Translator"},
    "cf0505xt-1wr3": {"manufacturer": "MORNSUN", "part_name": "DC/DC Converter"},
    "iam-20680ht": {"manufacturer": "TDK InvenSense", "part_name": "IMU Sensor"},
    "attiny1616-szt-vao": {"manufacturer": "Microchip", "part_name": "MCU"},
    "tlv9001qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Op-Amp"},
    "qmc5883l": {"manufacturer": "QST", "part_name": "Magnetometer"},
    "lm76202qpwprq1": {"manufacturer": "Texas Instruments", "part_name": "Ideal Diode Controller"},
    "bd83a04efv-me2": {"manufacturer": "Rohm Semiconductor", "part_name": "LED Driver"},
    "ecs-200-12-33q-jes-tr": {"manufacturer": "ECS Inc.", "part_name": "Crystal"},
    "y4ete00a0aa": {"manufacturer": "Quectel", "part_name": "LTE Module"},
    "yf0023aa": {"manufacturer": "Quectel", "part_name": "Wi-Fi/BT Antenna"},
}

CLUSTER_COMPONENT_KNOWLEDGE_BASE = {
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "MCU with Graphics", "manufacturer": "Spansion (Cypress)", "grade": "Automotive"},
    "veml6031x00": {"subsystem": "ALS Board", "part_name": "Ambient Light Sensor", "manufacturer": "Vishay", "grade": "Automotive"},
    "01270019-00": {"subsystem": "VIC Module", "part_name": "ANTENNA GPS", "manufacturer": "Unknown"},
    "01270020-00": {"subsystem": "VIC Module", "part_name": "ANTENNA WIFI", "manufacturer": "Unknown"},
    "01270021-00": {"subsystem": "VIC Module", "part_name": "ANTENNA LTE", "manufacturer": "Unknown"},
    "p0024-03": {"subsystem": "VIC Module", "part_name": "PCBA BOARD", "manufacturer": "Unknown"},
    "01270018-00": {"subsystem": "VIC Module", "part_name": "SENSOR ALS-PCBA", "manufacturer": "Unknown"},
}

# --- Helper Functions ---
def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}
        patterns = [
            r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$', r'^(.*?)\s*-->\s*(.+)$',
            r'^\d+:\s*([A-Z_]+):\s*"([A-Z]+)"$', r'^(.+?)\s+is\s+(success|failure|passed|failed)$',
            r'^(.+?)\s+(Failed|Passed)$',
        ]
        match = re.match(patterns[0], line, re.I)
        if match:
            test_data.update({"TestName": match.group(1).strip(), "Result": "PASS" if match.group(2).lower() in ["passed", "success"] else "FAIL", "Actual": match.group(3).strip()})
        elif (match := re.match(patterns[1], line, re.I)):
            result_str = match.group(2).lower()
            result = "PASS" if "passed" in result_str or "success" in result_str else "FAIL" if "failed" in result_str else "INFO"
            test_data.update({"TestName": match.group(1).strip(), "Result": result, "Actual": match.group(2).strip()})
        elif (match := re.match(patterns[2], line)):
            test_data.update({"TestName": match.group(1).strip().replace("_", " "), "Result": match.group(2).strip()})
        elif (match := re.match(patterns[3], line, re.I)):
            test_data.update({"TestName": match.group(1).strip(), "Result": "PASS" if match.group(2).lower() in ["success", "passed"] else "FAIL"})
        elif (match := re.match(patterns[4], line, re.I)):
            test_data.update({"TestName": match.group(1).strip(), "Result": "PASS" if match.group(2).lower() == "passed" else "FAIL"})
        else: continue
        for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
            if keyword in test_data["TestName"].lower(): test_data["Standard"] = standard
        extracted_tests.append(test_data)
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        file_extension = os.path.splitext(uploaded_file.name.lower())[1]
        if file_extension in ['.csv', '.xlsx']:
            df = pd.read_csv(uploaded_file) if file_extension == '.csv' else pd.read_excel(uploaded_file)
            df.columns = [str(c).strip().lower() for c in df.columns]
            rename_map = {'test': 'TestName', 'standard': 'Standard', 'expected': 'Expected', 'actual': 'Actual', 'result': 'Result', 'description': 'Description', 'part': 'TestName', 'manufacturer pn': 'Actual'}
            df.rename(columns=rename_map, inplace=True)
            return df.to_dict('records')
        elif file_extension == '.pdf':
             with pdfplumber.open(uploaded_file) as pdf: content = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())
        else: content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing: {e}")
        return []

def display_test_card(test_case, color):
    details = f"<b>🧪 Test:</b> {test_case.get('TestName', 'N/A')}<br>"
    for key, label in {'Standard': '📘 Standard', 'Expected': '🎯 Expected', 'Actual': '📌 Actual', 'Description': '💬 Description'}.items():
        if pd.notna(value := test_case.get(key)) and str(value).strip() and str(value).lower() not in ['—', 'nan']:
            details += f"<b>{label}:</b> {value}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details}</div>", unsafe_allow_html=True)

def display_component_details(part_number, data):
    st.markdown(f"<div class='component-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='component-title'>{data.get('part_name', 'N/A')} ({part_number.upper()})</div>", unsafe_allow_html=True)
    details = f"<div class='component-detail'><b>Manufacturer:</b> {data.get('manufacturer', 'N/A')}</div>"
    if 'subsystem' in data: details += f"<div class='component-detail'><b>Subsystem:</b> {data.get('subsystem')}</div>"
    if 'grade' in data: details += f"<div class='component-detail'><b>Grade:</b> {data.get('grade')}</div>"
    vmin, vmax = data.get('voltage_min'), data.get('voltage_max')
    if vmin is not None and vmax is not None: details += f"<div class='component-detail'><b>Voltage:</b> {vmin}V to {vmax}V</div>"
    elif vmax is not None: details += f"<div class='component-detail'><b>Voltage (Max):</b> {vmax}V</div>"
    if 'current_max' in data: details += f"<div class='component-detail'><b>Current (Max):</b> {data['current_max']}A</div>"
    tmin, tmax = data.get('temp_min'), data.get('temp_max')
    if tmin is not None and tmax is not None: details += f"<div class='component-detail'><b>Temp Range:</b> {tmin}°C to {tmax}°C</div>"
    st.markdown(details, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Test Requirement Generation", "Component Information", "Dashboard & Analytics"))
st.sidebar.info("An integrated tool for automotive compliance.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload reports (PDF, TXT, CSV, XLSX) to extract and display all relevant data.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv", "txt", "log"])
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            passed = [t for t in parsed_data if "PASS" in str(t.get("Result", "")).upper()]
            failed = [t for t in parsed_data if "FAIL" in str(t.get("Result", "")).upper()]
            others = [t for t in parsed_data if not ("PASS" in str(t.get("Result", "")).upper() or "FAIL" in str(t.get("Result", "")).upper())]
            st.markdown(f"### Found {len(passed)} Passed, {len(failed)} Failed, and {len(others)} Other items.")
            if passed:
                with st.expander("✅ Passed Cases", expanded=True):
                    for t in passed: display_test_card(t, '#1e9f50')
            if failed:
                with st.expander("🔴 Failed Cases", expanded=True):
                    for t in failed: display_test_card(t, '#c43a31')
            if others:
                with st.expander("ℹ️ Other/Informational Items", expanded=False):
                    for t in others: display_test_card(t, '#808080')
        else:
            st.warning("No recognizable data was extracted.")

# --- Other Modules ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Test Requirements", anchor=False)
    st.caption("Enter test cases to generate formal requirements.")
    text = st.text_area("Test cases (one per line)", "ip rating\nshort circuit test", height=100)
    if st.button("Generate Requirements"):
        cases = [l.strip() for l in text.split("\n") if l.strip()]
        if cases:
            st.session_state.requirements_generated += len(cases)
            st.markdown("#### Generated Requirements")
            for i, case in enumerate(cases):
                req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if key in case.lower()), None)
                html = f"<div class='card' style='border-left-color:#7c3aed;'><b>Test Case:</b> {case.title()}<br><b>Req ID:</b> REQ_{i+1:03d}<br>"
                html += f"<b>Description:</b> {req['requirement']}<br><b>Equipment:</b> {', '.join(req['equipment'])}" if req else "<b>Description:</b> Generic requirement - system must be tested."
                st.markdown(html + "</div>", unsafe_allow_html=True)

elif option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts across all internal databases for detailed specifications.")
    COMBINED_DB = {**COMPONENT_KNOWLEDGE_BASE, **CLUSTER_COMPONENT_KNOWLEDGE_BASE}
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., tle4275g, tlv9001qdckrq1").lower().strip()
    if st.button("Find Component"):
        if part_q:
            key = next((k for k in COMBINED_DB if part_q in k.lower()), None)
            if key:
                st.session_state.found_component = {"part_number": key, **COMBINED_DB[key]}
            else:
                st.session_state.found_component = {}
                st.warning("Component not found. Use external research links:")
                c1, c2, c3 = st.columns(3); c1.link_button("Octopart", f"https://octopart.com/search?q={part_q}"); c2.link_button("Digi-Key", f"https://www.digikey.com/en/products/result?s={part_q}"); c3.link_button("Google", f"https://www.google.com/search?q={part_q}+datasheet")
    if st.session_state.found_component:
        display_component_details(st.session_state.found_component['part_number'], st.session_state.found_component)
    st.markdown("---")
    with st.form("component_form", clear_on_submit=True):
        st.markdown("### Add Component to Project Database")
        d = st.session_state.get('found_component', {})
        pn = st.text_input("Part Number", value=d.get("part_number", ""))
        mfg = st.text_input("Manufacturer", value=d.get("manufacturer", ""))
        func = st.text_input("Function / Part Name", value=d.get("part_name", ""))
        notes = st.text_area("Notes", value=d.get("subsystem", ""))
        if st.form_submit_button("Add Component to Project"):
            if pn:
                new_row = pd.DataFrame([{"Part Number": pn, "Manufacturer": mfg, "Function": func, "Notes": notes}])
                st.session_state.component_db = pd.concat([st.session_state.component_db, new_row], ignore_index=True)
                st.success(f"Component '{pn}' added to the temporary project database.")
    if not st.session_state.component_db.empty:
        st.markdown("#### Project-Specific Component List")
        st.dataframe(st.session_state.component_db, use_container_width=True)

else: # Dashboard
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in Temp DB", len(st.session_state.component_db))
