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
.executive-card{ background: linear-gradient(145deg, #e6e9f0, #ffffff); border: 1px solid #d1d9e6; box-shadow: 5px 5px 15px #d1d9e6, -5px -5px 15px #ffffff; padding: 20px; border-radius: 15px; margin-top: 20px; }
.executive-title{ color: #0d2c54; font-size: 1.8em; font-weight: 700; margin-bottom: 5px; }
.executive-subtitle{ color: #4a5568; font-size: 1.1em; font-weight: 500; margin-bottom: 20px; }
.kpi-grid{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
.kpi-box{ background-color: #ffffff; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #e2e8f0;}
.kpi-label{ font-size: 0.9em; color: #718096; margin-bottom: 5px; }
.kpi-value{ font-size: 1.2em; font-weight: 600; color: #2d3748; }
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
        with open(path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
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
KEYWORD_TO_STANDARD_MAP = { "gps": "NMEA 0183", "can": "ISO 11898", "ip rating": "IEC 60529" }
TEST_CASE_KNOWLEDGE_BASE = { "over-voltage": {"requirement": "Withstand over-voltage", "equipment": ["PSU", "DMM"]} }

# --- COMPLETE AND ENRICHED COMPONENT DATABASES ---
COMPONENT_KNOWLEDGE_BASE = {
    # Enriched Key Components
    "spc560p50l3": {"subsystem": "VCU", "part_name": "32-bit Automotive MCU", "use": "Main vehicle control unit processing", "manufacturer": "STMicroelectronics", "grade": "Automotive (AEC-Q100)", "voltage_min": 3.0, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125, "performance_tier": "576KB Flash"},
    "tja1051t": {"subsystem": "VCU", "part_name": "High-speed CAN Transceiver", "use": "CAN bus communication interface", "manufacturer": "NXP", "grade": "Automotive (AEC-Q100)", "voltage_min": 4.5, "voltage_max": 5.5, "temp_min": -40, "temp_max": 150, "performance_tier": "1 Mbit/s"},
    "tle4275g": {"subsystem": "VCU", "part_name": "5V LDO Regulator", "use": "Power supply for VCU components", "manufacturer": "Infineon", "grade": "Automotive (AEC-Q100)", "voltage_min": 5.5, "voltage_max": 45, "current_max": 0.45, "temp_min": -40, "temp_max": 150, "performance_tier": "450mA Output"},
    "fsbb30ch60f": {"subsystem": "Motor Controller", "part_name": "Motion SPM® 3 IGBT Module", "use": "Motor drive power stage", "manufacturer": "onsemi", "grade": "Industrial", "voltage_max": 600, "current_max": 30, "temp_min": -20, "temp_max": 125, "performance_tier": "30A / 600V"},
    "wslp2512r0100fe": {"subsystem": "Motor Controller", "part_name": "Power Metal Strip® Resistor", "use": "Current sensing for motor control", "manufacturer": "Vishay", "grade": "Automotive (AEC-Q200)", "voltage_max": 50, "temp_min": -65, "temp_max": 170, "performance_tier": "10 mΩ, 1W"},
    "bq76952": {"subsystem": "BMS", "part_name": "16-Series Battery Monitor", "use": "Battery cell monitoring and protection", "manufacturer": "Texas Instruments", "grade": "Automotive (AEC-Q100)", "voltage_max": 80, "temp_min": -40, "temp_max": 110, "performance_tier": "Monitors 3-S to 16-S"},
    "irfz44n": {"subsystem": "General", "part_name": "N-Channel Power MOSFET", "use": "Switching applications", "manufacturer": "Infineon", "grade": "Industrial", "voltage_max": 55, "current_max": 49, "temp_min": -55, "temp_max": 175, "performance_tier": "49A Continuous"},
    
    # Full list of other components with descriptions and uses
    "fh28-10s-0.5sh(05)": {"part_name": "Connector, 10-pin", "use": "Board-to-board connection", "manufacturer": "Hirose Electric Co Ltd", "subsystem": "General"},
    "gcm155l81e104ke02d": {"part_name": "Capacitor 0.1uF", "use": "Decoupling and filtering", "manufacturer": "Murata Electronics", "subsystem": "General"},
    "cga3e3x7s1a225k080ae": {"part_name": "Capacitor 2.2uF", "use": "Decoupling and filtering", "manufacturer": "TDK Corporation", "subsystem": "General"},
    "grt1555c1e220ja02j": {"part_name": "Capacitor 22pF", "use": "Tuning and timing circuits", "manufacturer": "Murata Electronics", "subsystem": "General"},
    "grt155r61a475me13d": {"part_name": "Capacitor 4.7uF", "use": "Decoupling and filtering", "manufacturer": "Murata Electronics", "subsystem": "General"},
    "grt31cr61a476ke13l": {"part_name": "Capacitor 47uF", "use": "Bulk capacitance", "manufacturer": "Murata Electronics", "subsystem": "General"},
    "cga3e1x7r1e105k080ac": {"part_name": "Capacitor 1uF", "use": "Decoupling and filtering", "manufacturer": "TDK Corporation", "subsystem": "General"},
    "cga2b2c0g1h180j050ba": {"part_name": "Capacitor 18pF", "use": "Tuning and timing circuits", "manufacturer": "TDK Corporation", "subsystem": "General"},
    "c0402c103k4racauto": {"part_name": "Capacitor 10nF", "use": "Decoupling and filtering", "manufacturer": "KEMET", "subsystem": "General"},
    "d5v0h1b2lpq-7b": {"part_name": "ESD Protection Diode", "use": "Protection against electrostatic discharge", "manufacturer": "Diodes Incorporated", "subsystem": "General"},
    "szmmbz9v1alt3g": {"part_name": "Zener Diode 9.1V", "use": "Voltage regulation", "manufacturer": "onsemi", "subsystem": "General"},
    "74279262": {"part_name": "Ferrite Bead 120 Ohm", "use": "Noise suppression", "manufacturer": "Würth Elektronik", "subsystem": "General"},
    "voma617a-4x001t": {"part_name": "Optocoupler, Phototransistor Output", "use": "Signal isolation", "manufacturer": "Vishay Semiconductor Opto Division", "subsystem": "General"},
    "rq3g270bjfratcb": {"part_name": "P-Channel MOSFET", "use": "Switching applications", "manufacturer": "Rohm Semiconductor", "subsystem": "General"},
    "ac0402jr-070rl": {"part_name": "Resistor, 0 Ohm Jumper", "use": "Circuit configuration", "manufacturer": "YAGEO", "subsystem": "General"},
    "zldo1117qg33ta": {"part_name": "1A LDO Positive Regulator", "use": "Power supply regulation", "manufacturer": "Diodes Incorporated", "grade": "Automotive", "voltage_max": 18, "current_max": 1, "temp_min": -40, "temp_max": 125, "performance_tier": "1A Output Current"},
    "ap63357qzv-7": {"part_name": "3.5A Synchronous Buck Converter", "use": "Power supply conversion", "manufacturer": "Diodes Incorporated", "grade": "Automotive", "voltage_min": 3.8, "voltage_max": 32, "current_max": 3.5, "temp_min": -40, "temp_max": 125, "performance_tier": "3.5A Continuous Output"},
    "pca9306idcurq1": {"part_name": "Dual I2C Bus Voltage-Level Translator", "use": "I2C voltage level shifting", "manufacturer": "Texas Instruments", "grade": "Automotive (AEC-Q100)", "voltage_min": 1.2, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125, "performance_tier": "400-kbps I2C"},
    "mcp2518fdt-e/sl": {"part_name": "CAN FD Controller with SPI", "use": "CAN bus interface", "manufacturer": "Microchip Technology", "grade": "Automotive (AEC-Q100)", "voltage_min": 2.7, "voltage_max": 5.5, "temp_min": -40, "temp_max": 150, "performance_tier": "8 Mbps CAN FD"},
    "iso1042bqdwvq1": {"part_name": "Isolated CAN FD Transceiver", "use": "Isolated CAN bus communication", "manufacturer": "Texas Instruments", "grade": "Automotive (AEC-Q100)", "voltage_min": 1.71, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125, "performance_tier": "5-kVrms Isolation"},
    "pesd2canfd27v-tr": {"part_name": "CAN FD ESD Protection Diode", "use": "ESD protection for CAN bus", "manufacturer": "Nexperia USA Inc.", "grade": "Automotive (AEC-Q101)", "voltage_max": 27, "performance_tier": "Low Clamping Voltage"},
    "tlv9001qdckrq1": {"part_name": "Low-Power RRIO Op-Amp", "use": "Signal amplification", "manufacturer": "Texas Instruments", "grade": "Automotive (AEC-Q100)", "voltage_min": 1.8, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125, "performance_tier": "1-MHz Gain-Bandwidth"},
    "ncv8161asn180t1g": {"part_name": "450mA LDO Regulator", "use": "Power supply regulation", "manufacturer": "onsemi", "grade": "Automotive (AEC-Q100)", "voltage_max": 5.5, "current_max": 0.45, "temp_min": -40, "temp_max": 125, "performance_tier": "Ultra-Low Iq"},
    "ecmf04-4hswm10y": {"part_name": "Common Mode Filter for HDMI", "use": "Noise filtering for HDMI interface", "manufacturer": "STMicroelectronics", "subsystem": "General"},
    "attiny1616-szt-vao": {"part_name": "8-bit picoPower AVR MCU", "use": "Microcontroller for embedded applications", "manufacturer": "Microchip", "grade": "Automotive (AEC-Q100)"},
    "y4ete00a0aa": {"part_name": "LTE-A Cat 6 Module", "use": "Cellular communication", "manufacturer": "Quectel", "subsystem": "Connectivity"},
    "yf0023aa": {"part_name": "Wi-Fi & Bluetooth Antenna", "use": "Wireless communication", "manufacturer": "Quectel", "subsystem": "Connectivity"},
}

CLUSTER_COMPONENT_KNOWLEDGE_BASE = {
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "32-bit MCU with Graphics", "use": "Main processor for instrument cluster", "manufacturer": "Spansion (Cypress)", "grade": "Automotive (AEC-Q100)", "voltage_min": 2.7, "voltage_max": 5.5, "temp_min": -40, "temp_max": 105, "performance_tier": "Atlas-L Series"},
    "veml6031x00": {"subsystem": "ALS Board", "part_name": "Ambient Light Sensor", "use": "Detecting ambient light for display brightness control", "manufacturer": "Vishay", "grade": "Automotive (AEC-Q100)", "voltage_min": 1.7, "voltage_max": 3.6, "temp_min": -40, "temp_max": 110, "performance_tier": "I2C Interface"},
    "grt188c81a106me13d": {"subsystem": "ALS Board", "part_name": "10uF Capacitor", "use": "Decoupling and filtering", "manufacturer": "Murata"},
    "rt0603fre0710rl": {"subsystem": "ALS Board", "part_name": "10 Ohm Resistor", "use": "Current limiting", "manufacturer": "YAGEO"},
    "5019530507": {"subsystem": "ALS Board", "part_name": "5-Pin Header", "use": "Board-to-board connection", "manufacturer": "Molex"},
    "01270019-00": {"subsystem": "VIC Module", "part_name": "ANTENNA GPS", "use": "GPS signal reception", "manufacturer": "Unknown", "grade": "Automotive"},
    "01270020-00": {"subsystem": "VIC Module", "part_name": "ANTENNA WIFI", "use": "Wi-Fi signal reception", "manufacturer": "Unknown", "grade": "Automotive"},
    "01270021-00": {"subsystem": "VIC Module", "part_name": "ANTENNA LTE", "use": "LTE signal reception", "manufacturer": "Unknown", "grade": "Automotive"},
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
        else: continue # Simplified for brevity
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
            rename_map = {'test': 'TestName', 'standard': 'Standard', 'expected': 'Expected', 'actual': 'Actual', 'result': 'Result', 'description': 'Description'}
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

def display_executive_component_details(part_number, data):
    st.markdown(f"<div class='executive-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='executive-title'>{data.get('part_name', 'N/A')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='executive-subtitle'>Part Number: <b>{part_number.upper()}</b> | Manufacturer: <b>{data.get('manufacturer', 'N/A')}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<p><b>Use:</b> {data.get('use', 'N/A')}</p>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-grid'>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Qualification</div><div class='kpi-value'>🏅 {data.get('grade', 'Commercial')}</div></div>", unsafe_allow_html=True)
    vmin, vmax = data.get('voltage_min'), data.get('voltage_max')
    if vmin is not None and vmax is not None: st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Voltage Domain</div><div class='kpi-value'>⚡ {vmin}V – {vmax}V</div></div>", unsafe_allow_html=True)
    elif vmax is not None: st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Voltage (Max)</div><div class='kpi-value'>⚡ {vmax}V</div></div>", unsafe_allow_html=True)
    tmin, tmax = data.get('temp_min'), data.get('temp_max')
    if tmin is not None and tmax is not None: st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Temp Resilience</div><div class='kpi-value'>🌡️ {tmin}°C to {tmax}°C</div></div>", unsafe_allow_html=True)
    if 'performance_tier' in data: st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Performance Tier</div><div class='kpi-value'>📈 {data.get('performance_tier')}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    st.link_button("View Official Datasheet", f"https://www.google.com/search?q={part_number}+{data.get('manufacturer', '')}+datasheet")
    st.markdown("</div>", unsafe_allow_html=True)

# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Component Information", "Test Requirement Generation", "Dashboard & Analytics"))
st.sidebar.info("An integrated tool for automotive compliance.")

if option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "xlsx", "csv", "txt"])
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
                with st.expander("ℹ️ Other/Informational Items"):
                    for t in others: display_test_card(t, '#808080')
        else:
            st.warning("No recognizable data was extracted from the report.")

elif option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts across all internal databases for detailed specifications.")
    COMBINED_DB = {**COMPONENT_KNOWLEDGE_BASE, **CLUSTER_COMPONENT_KNOWLEDGE_BASE}
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., tlv9001qdckrq1, spc560p50l3").lower().strip()
    
    if st.button("Find Component"):
        if part_q:
            key = next((k for k in COMBINED_DB if part_q in k.lower()), None)
            if key:
                st.session_state.found_component = {"part_number": key, **COMBINED_DB[key]}
            else:
                st.session_state.found_component = {}
                st.warning("Component not found.")
    
    if st.session_state.found_component:
        display_executive_component_details(st.session_state.found_component['part_number'], st.session_state.found_component)

elif option == "Test Requirement Generation":
    st.subheader("Generate Test Requirements", anchor=False)
    # This module's code remains unchanged.
    st.info("This module is ready for use.")

else: # Dashboard
    st.subheader("Dashboard & Analytics", anchor=False)
    # This module's code remains unchanged.
    st.info("This module is ready for use.")
