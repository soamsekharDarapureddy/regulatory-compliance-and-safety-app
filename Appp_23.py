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

# ===============================================
# === GLOBAL CONFIG & STYLING ===
# ===============================================
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

st.markdown("""
<style>
:root { --accent:#0056b3; --panel:#f3f8fc; --shadow:#cfe7ff; }
.card{background:#fff; border-radius:10px; padding:12px 14px; margin-bottom:10px; border-left:8px solid #c9d6e8;}
.datasheet-card{ background: #ffffff; border: 1px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 20px; border-radius: 15px; margin-top: 20px; }
.datasheet-title{ color: #0056b3; font-size: 1.8em; font-weight: 700; margin-bottom: 5px; }
.datasheet-subtitle{ color: #4a5568; font-size: 1.1em; font-weight: 500; margin-bottom: 15px; }
.spec-grid{ display: grid; grid-template-columns: 1fr 2fr; gap: 10px 20px; align-items: center; }
.spec-label{ font-weight: 600; color: #495057; text-align: right; }
.spec-value{ color: #212529; }
a {text-decoration: none; color: #0056b3; font-weight: 500;}
a:hover {text-decoration: underline;}
.main .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ===============================================
# === HEADER AND LOGO ===
# ===============================================
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

# ===============================================
# === KNOWLEDGE BASES & DATABASE LOADING ===
# ===============================================
@st.cache_data
def load_bom_data(filepath='PCBA-SVIC_3.3_31Dec24_BOM.xlsx'):
    try:
        if not os.path.exists(filepath):
            st.error(f"BOM file not found. Please ensure '{filepath}' is in the same directory.")
            return {}
        
        df = pd.read_excel(filepath, sheet_name='SVIC_3V3', header=1)
        df.columns = [str(c).strip().lower() for c in df.columns]

        bom_db = {}
        for _, row in df.iterrows():
            part_num = str(row.get('manufacturer pn', '')).strip()
            part_desc = str(row.get('part', '')).strip()
            manufacturer = str(row.get('manufacturer', '')).strip()

            if not part_num or pd.isna(part_num) or part_num == 'nan':
                continue
            
            use = "General Purpose Component"
            if "capacitor" in part_desc.lower() or "uf" in part_desc.lower() or "pf" in part_desc.lower() or "nf" in part_desc.lower():
                use = f"Capacitor, {part_desc}, for Decoupling/Filtering"
            elif "resistor" in part_desc.lower() or ("r" in part_desc.lower() and ("k" in part_desc.lower() or "m" in part_desc.lower())):
                use = f"Resistor, {part_desc}, for Biasing/Pull-up/Pull-down"
            elif "diode" in part_desc.lower():
                use = f"Diode, {part_desc}, for Protection or Rectification"
            elif "connector" in part_desc.lower() or "header" in part_desc.lower():
                use = f"{part_desc} for Board-to-board/Wire connection"
            elif "mosfet" in part_desc.lower():
                use = "MOSFET for Switching applications"
            elif "antenna" in part_desc.lower():
                use = f"{part_desc} for RF Signal Reception/Transmission"
            elif "mcu" in part_desc.lower() or "attiny" in part_desc.lower() or "spc560p50l3" in part_desc.lower():
                use = "Microcontroller Unit for processing"
            elif "ferrite" in part_desc.lower() or "bead" in part_desc.lower() or "@" in part_desc.lower():
                use = f"Ferrite Bead, {part_desc}, for EMI Suppression"
            elif "inductor" in part_desc.lower() or "uh" in part_desc.lower() or "nh" in part_desc.lower():
                use = "Inductor for Power Conversion or Filtering"

            bom_db[part_num.lower()] = {
                'part_name': f"{part_desc} ({part_num})",
                'manufacturer': manufacturer,
                'use': use,
            }
        return bom_db
    except Exception as e:
        st.error(f"Error loading BOM file: {e}")
        return {}

ENRICHED_DB = {
    "ecmf04-4hswm10y": {
        "part_name": "Common Mode Filter with ESD Protection", "use": "EMI/RFI filtering and ESD protection for high-speed differential lines.",
        "manufacturer": "STMicroelectronics", "category": "Filters", "sub_category": "Common Mode Chokes", "series": "ECMF",
        "packaging": "Tape & Reel (TR)", "part_status": "Active", "filter_type": "Signal Line", "number_of_lines": 4,
        "current_rating_max_ma": 100, "dcr_max_ohm": 5, "operating_temp_min_c": -40, "operating_temp_max_c": 85,
        "features": "TVS Diode ESD Protection", "mounting_type": "Surface Mount", "size_dimension_mm": "2.60mm x 1.35mm",
        "height_max_mm": 0.55, "package_case": "10-UFDFN", "base_product_number": "ECMF04"
    },
    "tlv9001qdckrq1": {"part_name": "Low-Power RRIO Op-Amp", "use": "Signal amplification in sensor interfaces and control loops", "manufacturer": "Texas Instruments", "grade": "Automotive (AEC-Q100)", "voltage_min": 1.8, "voltage_max": 5.5, "temp_min": -40, "temp_max": 125, "performance_tier": "1-MHz Gain-Bandwidth"},
}

COMBINED_DB = {**load_bom_data(), **ENRICHED_DB}
KEYWORD_TO_STANDARD_MAP = { "gps": "NMEA 0183", "can": "ISO 11898", "ip rating": "IEC 60529" }
TEST_CASE_KNOWLEDGE_BASE = { "over-voltage": {"requirement": "Withstand over-voltage", "equipment": ["PSU", "DMM"]} }

# ===============================================
# === HELPER FUNCTIONS (FOR ALL MODULES) ===
# ===============================================
def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        test_data = {"TestName": "N/A", "Result": "N/A", "Standard": "N/A", "Description": "N/A"}
        patterns = [
            r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$',
            r'^(.*?)\s*:\s*(PASS|FAIL|PASSED|FAILED)$'
        ]
        match1 = re.match(patterns[0], line, re.I)
        match2 = re.match(patterns[1], line, re.I)
        if match1:
            test_data.update({"TestName": match1.group(1).strip(), "Result": "PASS" if match1.group(2).lower() in ["passed", "success"] else "FAIL", "Description": match1.group(3).strip()})
        elif match2:
            test_data.update({"TestName": match2.group(1).strip(), "Result": "PASS" if match2.group(2).lower() in ["pass", "passed"] else "FAIL"})
        else:
            continue
        for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
            if keyword in test_data["TestName"].lower():
                test_data["Standard"] = standard
        extracted_tests.append(test_data)
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        file_extension = os.path.splitext(uploaded_file.name.lower())[1]
        if file_extension in ['.csv', '.xlsx']:
            df = pd.read_csv(uploaded_file) if file_extension == '.csv' else pd.read_excel(uploaded_file)
            df.columns = [str(c).strip().lower() for c in df.columns]
            rename_map = {'test': 'TestName', 'standard': 'Standard', 'result': 'Result', 'description': 'Description'}
            df.rename(columns=rename_map, inplace=True)
            return df.to_dict('records')
        elif file_extension == '.pdf':
             with pdfplumber.open(uploaded_file) as pdf:
                content = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())
        else:
            content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing the report: {e}")
        return []

def display_test_card(test_case, color):
    details = f"<b>🧪 Test:</b> {test_case.get('TestName', 'N/A')}<br>"
    for key, label in {'Standard': '📘 Standard', 'Description': '💬 Description'}.items():
        if pd.notna(value := test_case.get(key)) and str(value).strip() and value != 'N/A':
            details += f"<b>{label}:</b> {value}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details}</div>", unsafe_allow_html=True)

def display_datasheet_details(part_number, data):
    st.markdown(f"<div class='datasheet-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='datasheet-title'>{data.get('part_name', part_number.upper())}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='datasheet-subtitle'><b>Manufacturer:</b> {data.get('manufacturer', 'N/A')}</div>", unsafe_allow_html=True)
    st.markdown(f"<p><b>Primary Use / Application:</b> {data.get('use', 'General Purpose')}</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 1px solid #e9ecef; margin: 15px 0;'>", unsafe_allow_html=True)
    
    st.markdown("<div class='spec-grid'>", unsafe_allow_html=True)
    spec_order = [
        ("Category", "category"), ("Series", "series"), ("Packaging", "packaging"), ("Part Status", "part_status"),
        ("Filter Type", "filter_type"), ("Number of Lines", "number_of_lines"),
        ("Current Rating (Max)", "current_rating_max_ma", "mA"), ("DC Resistance (Max)", "dcr_max_ohm", "Ohm"),
        ("Operating Temperature", "operating_temp_range"), ("Features", "features"), ("Mounting Type", "mounting_type"),
        ("Size / Dimension", "size_dimension_mm"), ("Height (Max)", "height_max_mm", "mm"),
        ("Package / Case", "package_case"), ("Base Product Number", "base_product_number")
    ]
    if "operating_temp_min_c" in data and "operating_temp_max_c" in data:
        data["operating_temp_range"] = f"{data['operating_temp_min_c']}°C ~ {data['operating_temp_max_c']}°C"
    
    has_specs = False
    for label, key, *unit in spec_order:
        if key in data and data.get(key):
            has_specs = True
            value = f"{data[key]}{unit[0]}" if unit and data[key] else data[key]
            st.markdown(f"<div class='spec-label'>{label}</div><div class='spec-value'>{value}</div>", unsafe_allow_html=True)
            
    if not has_specs:
        st.markdown("<div class='spec-label'>Details</div><div class='spec-value'>Standard component data loaded from BOM. For full datasheet specifications, please refer to the manufacturer's website.</div>", unsafe_allow_html=True)
        
    st.markdown("</div></div>", unsafe_allow_html=True)

# ===============================================
# === MAIN APP LAYOUT & NAVIGATION ===
# ===============================================
st.sidebar.title("Navigation")
option = st.sidebar.radio("Go to", ("Test Report Verification", "Component Information", "Test Requirement Generation"))

# ===============================================
# === 1. TEST REPORT VERIFICATION MODULE ===
# ===============================================
if option == "Test Report Verification":
    st.header("Test Report Verification")
    st.caption("Upload and analyze test reports from various formats.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "xlsx", "csv", "txt"])
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.success(f"Successfully parsed {len(parsed_data)} test results.")
            passed = [t for t in parsed_data if "PASS" in str(t.get("Result", "")).upper()]
            failed = [t for t in parsed_data if "FAIL" in str(t.get("Result", "")).upper()]
            others = [t for t in parsed_data if not ("PASS" in str(t.get("Result", "")).upper() or "FAIL" in str(t.get("Result", "")).upper())]
            
            st.markdown(f"### Analysis Complete: {len(passed)} Passed, {len(failed)} Failed, {len(others)} Other")
            if passed:
                with st.expander("✅ Passed Cases", expanded=True):
                    for t in passed: display_test_card(t, '#28a745')
            if failed:
                with st.expander("❌ Failed Cases", expanded=True):
                    for t in failed: display_test_card(t, '#dc3545')
            if others:
                with st.expander("ℹ️ Other/Informational Items"):
                    for t in others: display_test_card(t, '#6c757d')
        else:
            st.warning("No recognizable test data was extracted from the report.")

# ===============================================
# === 2. COMPONENT INFORMATION MODULE ===
# ===============================================
elif option == "Component Information":
    st.header("Component Key Information")
    st.caption("Search the complete BOM for detailed component specifications.")
    
    part_q = st.text_input("Enter Manufacturer Part Number for Detailed Lookup", placeholder="e.g., ecmf04-4hswm10y").lower().strip()
    
    if st.button("Search Component"):
        if part_q:
            key = next((k for k in COMBINED_DB if part_q in k.lower()), None)
            if key:
                st.session_state.found_component = {"part_number": key, **COMBINED_DB[key]}
            else:
                st.session_state.found_component = {}
                st.warning("Component not found in the internal database.")
    
    if 'found_component' in st.session_state and st.session_state.found_component:
        display_datasheet_details(st.session_state.found_component['part_number'], st.session_state.found_component)

# ===============================================
# === 3. TEST REQUIREMENT GENERATION MODULE ===
# ===============================================
elif option == "Test Requirement Generation":
    st.header("Test Requirement Generation")
    st.caption("Automatically generate formal test requirements from keywords.")
    
    text = st.text_area("Enter test keywords (one per line)", "over-voltage test\nCAN bus functionality\nIP67 rating check", height=100)
    
    if st.button("Generate Requirements"):
        cases = [l.strip() for l in text.split("\n") if l.strip()]
        if cases:
            st.markdown("#### Generated Requirements")
            for i, case in enumerate(cases):
                req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if key in case.lower()), {"requirement": "Generic requirement - system must be tested as described.", "equipment": ["N/A"]})
                html = f"""
                <div class='card' style='border-left-color:#7c3aed;'>
                    <b>Test Case:</b> {case.title()}<br>
                    <b>Requirement ID:</b> REQ-{i+1:03d}<br>
                    <b>Requirement:</b> {req['requirement']}<br>
                    <b>Suggested Equipment:</b> {', '.join(req['equipment'])}
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
