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
    "gps": "NMEA 0183", "gnss": "3GPP", "bluetooth": "Bluetooth Core Specification", "wifi": "IEEE 802.11",
    "lte": "3GPP LTE", "can": "ISO 11898", "sensor": "AEC-Q104", "ip rating": "IEC 60529",
    "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156", "vibration": "IEC 60068-2-6"
}
TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage": {"requirement": "DUT must withstand over-voltage.", "equipment": ["DC Power Supply", "DMM"]},
    "short circuit": {"requirement": "DUT shall safely interrupt short-circuit.", "equipment": ["High-Current Supply", "Oscilloscope"]},
    "vibration": {"requirement": "DUT must withstand vibration without mechanical failure.", "equipment": ["Shaker Table"]},
}

# --- MODIFICATION: Expanded Component Databases ---
# Main database for non-cluster parts
COMPONENT_KNOWLEDGE_BASE = {
    # VCU, Motor Controller, Charger, BMS
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit MCU", "manufacturer": "STMicroelectronics", "certifications": "AEC-Q100"},
    "tja1051t": {"subsystem": "VCU", "part_name": "CAN Transceiver", "manufacturer": "NXP", "certifications": "AEC-Q100"},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V LDO Regulator", "manufacturer": "Infineon", "certifications": "AEC-Q100"},
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "IGBT Module", "manufacturer": "ON Semi"},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Current Sense Resistor", "manufacturer": "Vishay"},
    "bq76952": {"subsystem": "BMS", "part_name": "Battery Monitor", "manufacturer": "Texas Instruments"},
    
    # General Purpose and Newly Added Components
    "irfz44n": {"subsystem": "General", "part_name": "MOSFET", "manufacturer": "Infineon"},
    "1n4007": {"subsystem": "General", "part_name": "Diode", "manufacturer": "Multiple"},
    "fh28-10s-0.5sh(05)": {"manufacturer": "Hirose Electric Co Ltd", "part_name": "Connector", "subsystem": "General"},
    "gcm155l81e104ke02d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "cga3e3x7s1a225k080ae": {"manufacturer": "TDK Corporation", "part_name": "Capacitor", "subsystem": "General"},
    "grt1555c1e220ja02j": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt155r61a475me13d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt31cr61a476ke13l": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "cga3e1x7r1e105k080ac": {"manufacturer": "TDK Corporation", "part_name": "Capacitor", "subsystem": "General"},
    "cga2b2c0g1h180j050ba": {"manufacturer": "TDK Corporation", "part_name": "Capacitor", "subsystem": "General"},
    "c0402c103k4racauto": {"manufacturer": "KEMET", "part_name": "Capacitor", "subsystem": "General"},
    "gcm1555c1h101ja16d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt155r71h104ke01d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt21br61e226me13l": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt1555c1h150fa02d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "0402yc222j4t2a": {"manufacturer": "KYOCERA AVX", "part_name": "Capacitor", "subsystem": "General"},
    "gcm1555c1h560fa16d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "grt1555c1h330fa02d": {"manufacturer": "Murata Electronics North America", "part_name": "Capacitor", "subsystem": "General"},
    "grt188c81a106me13d": {"manufacturer": "Murata Electronics North America", "part_name": "Capacitor", "subsystem": "General"},
    "umk212b7105kght": {"manufacturer": "Taiyo Yuden", "part_name": "Capacitor", "subsystem": "General"},
    "c1206c104k5racauto": {"manufacturer": "KEMET", "part_name": "Capacitor", "subsystem": "General"},
    "grt31cr61h106ke01k": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "mcasu105sb7103kfna01": {"manufacturer": "Taiyo Yuden", "part_name": "Capacitor", "subsystem": "General"},
    "c0402c333k4racauto": {"manufacturer": "KEMET", "part_name": "Capacitor", "subsystem": "General"},
    "cl10b474ko8vpnc": {"manufacturer": "Samsung Electro-Mechanics", "part_name": "Capacitor", "subsystem": "General"},
    "gcm155r71c224ke02d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "gcm155r71h102ka37j": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "50tpv330m10x10.5": {"manufacturer": "Rubycon", "part_name": "Capacitor", "subsystem": "General"},
    "cl31b684kbhwpne": {"manufacturer": "Samsung Electro-Mechanics", "part_name": "Capacitor", "subsystem": "General"},
    "gcm155r71h272ka37d": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "edk476m050s9haa": {"manufacturer": "KEMET", "part_name": "Capacitor", "subsystem": "General"},
    "gcm155r71h332ka37j": {"manufacturer": "Murata Electronics", "part_name": "Capacitor", "subsystem": "General"},
    "a768ke336m1hlae042": {"manufacturer": "KEMET", "part_name": "Capacitor", "subsystem": "General"},
    "ac0402jrx7r9bb152": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "d5v0h1b2lpq-7b": {"manufacturer": "Diodes Incorporated", "part_name": "Diode", "subsystem": "General"},
    "szmmbz9v1alt3g": {"manufacturer": "onsemi", "part_name": "Diode", "subsystem": "General"},
    "d24v0s1u2tq-7": {"manufacturer": "Diodes Incorporated", "part_name": "Diode", "subsystem": "General"},
    "b340bq-13-f": {"manufacturer": "Diodes Incorporated", "part_name": "Diode", "subsystem": "General"},
    "tld8s22ah": {"manufacturer": "Taiwan Semiconductor", "part_name": "Diode", "subsystem": "General"},
    "b260aq-13-f": {"manufacturer": "Diodes Incorporated", "part_name": "Diode", "subsystem": "General"},
    "rb530sm-40fht2r": {"manufacturer": "Rohm Semiconductor", "part_name": "Diode", "subsystem": "General"},
    "74279262": {"manufacturer": "Würth Elektronik", "part_name": "Ferrite Bead", "subsystem": "General"},
    "742792641": {"manufacturer": "Würth Elektronik", "part_name": "Ferrite Bead", "subsystem": "General"},
    "742792625": {"manufacturer": "Würth Elektronik", "part_name": "Ferrite Bead", "subsystem": "General"},
    "742792150": {"manufacturer": "Würth Elektronik", "part_name": "Ferrite Bead", "subsystem": "General"},
    "78279220800": {"manufacturer": "Würth Elektronik", "part_name": "Ferrite Bead", "subsystem": "General"},
    "voma617a-4x001t": {"manufacturer": "Vishay Semiconductor Opto Division", "part_name": "Optocoupler", "subsystem": "General"},
    "534260610": {"manufacturer": "Molex", "part_name": "Connector", "subsystem": "General"},
    "fh52-40s-0.5sh(99)": {"manufacturer": "Hirose Electric Co Ltd", "part_name": "Connector", "subsystem": "General"},
    "x8821wv-06l-n0sn": {"manufacturer": "XKB", "part_name": "Connector", "subsystem": "General"},
    "744235510": {"manufacturer": "Würth Elektronik", "part_name": "Inductor", "subsystem": "General"},
    "lqw15an56nj8zd": {"manufacturer": "Murata Electronics", "part_name": "Inductor", "subsystem": "General"},
    "spm7054vt-220m-d": {"manufacturer": "TDK Corporation", "part_name": "Inductor", "subsystem": "General"},
    "744273801": {"manufacturer": "Wurth Electronics Inc", "part_name": "Inductor", "subsystem": "General"},
    "74404084068": {"manufacturer": "Würth Elektronik", "part_name": "Inductor", "subsystem": "General"},
    "744231091": {"manufacturer": "Würth Elektronik", "part_name": "Inductor", "subsystem": "General"},
    "mlz2012m6r8htd25": {"manufacturer": "TDK Corporation", "part_name": "Inductor", "subsystem": "General"},
    "rq3g270bjfratcb": {"manufacturer": "Rohm Semiconductor", "part_name": "MOSFET", "subsystem": "General"},
    "pja138k-au_r1_000a1": {"manufacturer": "Panjit International Inc.", "part_name": "MOSFET", "subsystem": "General"},
    "dmp2070uq-7": {"manufacturer": "Diodes Incorporated", "part_name": "MOSFET", "subsystem": "General"},
    "ac0402jr-070rl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "ac0402fr-07100kl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft158k": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft30k0": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft127k": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmc10k204fth": {"manufacturer": "KAMAYA", "part_name": "Resistor", "subsystem": "General"},
    "erj-2rkf2201x": {"manufacturer": "Panasonic Electronic Components", "part_name": "Resistor", "subsystem": "General"},
    "erj-2rkf1002x": {"manufacturer": "Panasonic Electronic Components", "part_name": "Resistor", "subsystem": "General"},
    "wr04x1004ftl": {"manufacturer": "Walsin Technology Corporation", "part_name": "Resistor", "subsystem": "General"},
    "wr04x10r0ftl": {"manufacturer": "Walsin Technology Corporation", "part_name": "Resistor", "subsystem": "General"},
    "rc0603fr-0759rl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "rmc1/16jptp": {"manufacturer": "Kamaya Inc.", "part_name": "Resistor", "subsystem": "General"},
    "ac0402fr-07100rl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "ac0402fr-076k04l": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "ac0402fr-07510rl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "crgcq0402f56k": {"manufacturer": "TE Connectivity Passive Product", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft24k9": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft5k36": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0603ft12k0": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft210k": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "ltr18ezpfsr015": {"manufacturer": "Rohm Semiconductor", "part_name": "Resistor", "subsystem": "General"},
    "erj-pa2j102x": {"manufacturer": "Panasonic Electronic Components", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft5k10": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0603ft100r": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "ac0402jr-074k7l": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "crf0805-fz-r010elf": {"manufacturer": "Bourns Inc.", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft3k16": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft3k48": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft1k50": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft4k02": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf1206zt0r00": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft402k": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "ac0603fr-7w20kl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "h164yp": {"manufacturer": "AGENEW", "part_name": "Unknown", "subsystem": "General"},
    "zldo1117qg33ta": {"manufacturer": "Diodes Incorporated", "part_name": "LDO Regulator", "subsystem": "General"},
    "ap63357qzv-7": {"manufacturer": "Diodes Incorporated", "part_name": "Switching Regulator", "subsystem": "General"},
    "pca9306idcurq1": {"manufacturer": "Texas Instruments", "part_name": "Level Translator", "subsystem": "General"},
    "mcp2518fdt-e/sl": {"manufacturer": "Microchip Technology", "part_name": "CAN Controller", "subsystem": "General"},
    "iso1042bqdwvq1": {"manufacturer": "Texas Instruments", "part_name": "CAN Transceiver", "subsystem": "General"},
    "pesd2canfd27v-tr": {"manufacturer": "Nexperia USA Inc.", "part_name": "ESD Protection", "subsystem": "General"},
    "lt8912b": {"manufacturer": "Lontium", "part_name": "MIPI DSI/CSI-2 Bridge", "subsystem": "General"},
    "sn74lv1t34qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Buffer", "subsystem": "General"},
    "ncp164csnadjt1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "20279-001e-03": {"manufacturer": "I-PEX", "part_name": "Connector", "subsystem": "General"},
    "ncv8161asn180t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "drtr5v0u2sr-7": {"manufacturer": "Diodes Incorporated", "part_name": "ESD Protection", "subsystem": "General"},
    "ncv8161asn330t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "ecmf04-4hswm10y": {"manufacturer": "STMicroelectronics", "part_name": "Common Mode Filter", "subsystem": "General"},
    "nxs0102dc-q100h": {"manufacturer": "Nexperia USA Inc.", "part_name": "Level Translator", "subsystem": "General"},
    "cf0505xt-1wr3": {"manufacturer": "MORNSUN", "part_name": "DC/DC Converter", "subsystem": "General"},
    "iam-20680ht": {"manufacturer": "TDK InvenSense", "part_name": "IMU Sensor", "subsystem": "General"},
    "attiny1616-szt-vao": {"manufacturer": "Microchip", "part_name": "MCU", "subsystem": "General"},
    "tlv9001qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Op-Amp", "subsystem": "General"},
    "qmc5883l": {"manufacturer": "QST", "part_name": "Magnetometer", "subsystem": "General"},
    "lm76202qpwprq1": {"manufacturer": "Texas Instruments", "part_name": "Ideal Diode Controller", "subsystem": "General"},
    "bd83a04efv-me2": {"manufacturer": "Rohm Semiconductor", "part_name": "LED Driver", "subsystem": "General"},
    "ecs-200-12-33q-jes-tr": {"manufacturer": "ECS Inc.", "part_name": "Crystal", "subsystem": "General"},
    "ecs-250-12-33q-jes-tr": {"manufacturer": "ECS Inc.", "part_name": "Crystal", "subsystem": "General"},
    "aggbp.25a.07.0060a": {"manufacturer": "Toaglas", "part_name": "GNSS Antenna", "subsystem": "General"},
    "y4ete00a0aa": {"manufacturer": "Quectel", "part_name": "LTE Module", "subsystem": "General"},
    "yf0023aa": {"manufacturer": "Quectel", "part_name": "Wi-Fi/BT Antenna", "subsystem": "General"},
}

# Database for Cluster-related parts
CLUSTER_COMPONENT_KNOWLEDGE_BASE = {
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "MCU with Graphics", "manufacturer": "Spansion (Cypress)"},
    "veml6031x00": {"subsystem": "ALS Board", "part_name": "Ambient Light Sensor", "manufacturer": "Vishay"},
    "01270019-00": {"subsystem": "VIC Module", "part_name": "ANTENNA GPS", "manufacturer": "Unknown"},
    "01270020-00": {"subsystem": "VIC Module", "part_name": "ANTENNA WIFI", "manufacturer": "Unknown"},
    "01270021-00": {"subsystem": "VIC Module", "part_name": "ANTENNA LTE", "manufacturer": "Unknown"},
    "p0024-03": {"subsystem": "VIC Module", "part_name": "PCBA BOARD", "manufacturer": "Unknown"},
    "01270018-00": {"subsystem": "VIC Module", "part_name": "SENSOR ALS-PCBA", "manufacturer": "Unknown"},
    "01270010-02": {"subsystem": "VIC Module", "part_name": "TFT LCD WITH COVER GLASS", "manufacturer": "Unknown"},
}


def intelligent_parser(text: str):
    # This function remains unchanged
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
        # Regex matching logic here...
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
        elif (match := re.match(patterns, line, re.I)):
            test_data.update({"TestName": match.group(1).strip(), "Result": "PASS" if match.group(2).lower() == "passed" else "FAIL"})
        else:
            continue
        
        for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
            if keyword in test_data["TestName"].lower():
                test_data["Standard"] = standard
                break
        extracted_tests.append(test_data)
    return extracted_tests

def parse_report(uploaded_file):
    # This function remains unchanged
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
    # This function remains unchanged
    details = f"<b>🧪 Test:</b> {test_case.get('TestName', 'N/A')}<br>"
    for key, label in {'Standard': '📘 Standard', 'Expected': '🎯 Expected', 'Actual': '📌 Actual', 'Description': '💬 Description'}.items():
        if pd.notna(value := test_case.get(key)) and str(value).strip() and str(value).lower() not in ['—', 'nan']:
            details += f"<b>{label}:</b> {value}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details}</div>", unsafe_allow_html=True)

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

# --- Other Modules (remain unchanged) ---
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
    st.caption("Look up parts across all internal databases.")
    COMBINED_DB = {**COMPONENT_KNOWLEDGE_BASE, **CLUSTER_COMPONENT_KNOWLEDGE_BASE}
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., irfz44n, veml6031x00").lower().strip()
    if st.button("Find Component"):
        key = next((k for k in COMBINED_DB if k in part_q), None)
        if key:
            st.session_state.found_component = {"part_number": key, **COMBINED_DB[key]}
            st.success(f"Found: {key.upper()}. Details populated below.")
        else:
            st.session_state.found_component = {}
            st.warning("Not in internal databases. Use research links:")
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
        notes = st.text_area("Notes (e.g., Subsystem, Certifications)", value=d.get("subsystem", d.get("certifications", "")))
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
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in Temp DB", len(st.session_state.component_db))
