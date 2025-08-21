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


# ============= Branding & Page Config =============
st.set_page_config(page_title="E-Bike Regulatory Compliance & Safety Checking tool", layout="wide")

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

# ============= NEW: ROBUST HEADER with LOGO and TITLE =============
def get_image_as_base64(path):
    """Function to embed a local image file into the HTML."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Get the base64 string of the logo
img_base64 = get_image_as_base64("logo.png")

# Create the HTML for the logo. If logo.png is not found, it will display the company name as text.
logo_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 100px; height: auto; margin-right: 20px;">' if img_base64 else '<h2 style="color:var(--accent);">People_TECH</h2>'

# Render the final header using a robust flexbox layout in HTML
st.markdown(f"""
<div style="display: flex; align-items: center; background:var(--panel); padding: 15px; border-radius: 14px; box-shadow: 0 2px 16px var(--shadow);">
    {logo_html}
    <div>
        <h1 style="color:var(--accent); font-size:1.8em; margin:0; line-height:1.2;">E‑Bike Regulatory Compliance & Safety Checking tool</h1>
        <p style="color:#555; margin:0; font-weight:500;">A People TECH Company Solution</p>
    </div>
</div>
<br>
""", unsafe_allow_html=True)


# ============= UPGRADED Keyword-to-Standard Mapping Engine =============
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

COMPONENT_KNOWLEDGE_BASE = {
    "bq76952": {"manufacturer": "Texas Instruments", "function": "Battery Monitor IC", "voltage": "Up to 80V"},
    "irfb4110": {"manufacturer": "Infineon", "function": "N‑MOSFET", "voltage": "100V", "current": "180A"},
    "1n4007": {"manufacturer": "Generic", "function": "Rectifier Diode", "voltage": "1000V", "current": "1A"},
}

# ============= Intelligent Parser for FCT and Formal Reports =============
def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue

        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}

        # Pattern 1: `Name --> Result --> Value`
        match1 = re.match(r'^(.+?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$', line, re.I)
        if match1:
            test_data["TestName"] = match1.group(1).strip()
            result_str = match1.group(2).lower()
            test_data["Result"] = "PASS" if "passed" in result_str or "success" in result_str else "FAIL"
            test_data["Actual"] = match1.group(3).strip()
            extracted_tests.append(test_data)
            continue

        # Pattern 2: `Name --> Result`
        match2 = re.match(r'^(.+?)\s*-->\s*(.+)$', line, re.I)
        if match2:
            test_data["TestName"] = match2.group(1).strip()
            result_str = match2.group(2).lower()
            if "passed" in result_str or "success" in result_str:
                test_data["Result"] = "PASS"
                test_data["Actual"] = match2.group(2).strip()
            elif "failed" in result_str:
                test_data["Result"] = "FAIL"
                test_data["Actual"] = match2.group(2).strip()
            else:
                test_data["Result"] = "INFO"
                test_data["Actual"] = match2.group(2).strip()
            extracted_tests.append(test_data)
            continue
            
        # Pattern 3: Diagnostic Report `Number: NAME: "RESULT"`
        match3 = re.match(r'^\d+:\s*([A-Z_]+):\s*"([A-Z]+)"$', line)
        if match3:
            test_data["TestName"] = match3.group(1).strip()
            result = match3.group(2).strip()
            test_data["Result"] = result if result in ["PASS", "FAIL"] else "NA"
            extracted_tests.append(test_data)
            continue
            
        # Pattern 4: Simple `Test Name is Success/Failure`
        match4 = re.match(r'^(.+?)\s+is\s+(success|failure|passed|failed)$', line, re.I)
        if match4:
            test_data["TestName"] = match4.group(1).strip()
            result_str = match4.group(2).lower()
            test_data["Result"] = "PASS" if "success" in result_str or "passed" in result_str else "FAIL"
            extracted_tests.append(test_data)
            continue

        # Pattern 5: Simple `Test Name Failed` or `Test Name Passed`
        match5 = re.match(r'^(.+?)\s+(Failed|Passed)$', line, re.I)
        if match5:
            test_data["TestName"] = match5.group(1).strip()
            test_data["Result"] = "PASS" if "passed" in match5.group(2).lower() else "FAIL"
            extracted_tests.append(test_data)
            continue

    # Associate known standards using the keyword map
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

# ============= Sidebar Navigation =============
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Test Requirement Generation", "Component Information", "Dashboard & Analytics"))
st.sidebar.info("This tool helps verify compliance reports, generate test requirements, and manage component data.")

# ============= Module: Test Report Verification (with Columns) =============
if option == "Test Report Verification":
    st.markdown('<div class="gem-panel" style="background: #fff;">', unsafe_allow_html=True)
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload PDF/DOCX reports. The parser intelligently extracts and groups tests by PASS/FAIL status into side-by-side columns.")

    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv"])
    if uploaded_file:
        parsed = parse_report(uploaded_file)
        if parsed:
            # --- Filter tests into groups ---
            failed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "FAIL"]
            passed_tests = [t for t in parsed if str(t.get("Result", "")).upper() == "PASS"]
            other_tests = [t for t in parsed if str(t.get("Result", "")).upper() not in ["PASS", "FAIL"]]

            # Create two columns for PASS and FAIL
            col1, col2 = st.columns(2)

            # --- Left Column: PASSED tests ---
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
            
            # --- Right Column: FAILED tests ---
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

            st.markdown("---") # Separator before other tests

            # --- Display OTHER tests below the columns in a collapsible expander ---
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
    st.markdown('</div>', unsafe_allow_html=True)

# ============= Module: Test Requirement Generation =============
elif option == "Test Requirement Generation":
    st.markdown('<div class="gem-panel">', unsafe_allow_html=True)
    st.subheader("Generate Test Requirements", anchor=False)
    st.caption("Enter one test per line to generate formal requirements and equipment lists.")
    default_cases = "ip rating\nshort circuit\nframe fatigue test"
    text = st.text_area("Test cases (one per line)", default_cases, height=120)
    if st.button("Generate Requirements"):
        test_cases = [l.strip() for l in text.split("\n") if l.strip()]
        if test_cases:
            reqs = []
            for i, case in enumerate(test_cases):
                found = False
                for key, info in TEST_CASE_KNOWLEDGE_BASE.items():
                    if key.replace(" test", "") in case.lower():
                        reqs.append({
                            "Test Case": key.title(), "Requirement ID": f"REQ_{i+1:03d}",
                            "Requirement Description": info["requirement"], "Required Equipment": ", ".join(info["equipment"])
                        })
                        found = True
                if not found:
                    reqs.append({
                        "Test Case": case, "Requirement ID": f"REQ_{i+1:03d}",
                        "Requirement Description": "Generic requirement: System must handle this case.", "Required Equipment": "Not specified.",
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
    st.markdown('</div>', unsafe_allow_html=True)

# ============= Module: Component Information =============
elif option == "Component Information":
    st.markdown('<div class="gem-panel">', unsafe_allow_html=True)
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts in the internal database or use web search shortcuts.")
    if "component_db" not in st.session_state: st.session_state.component_db = pd.DataFrame()
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., IRFB4110").lower().strip()
    if st.button("Find Component"):
        found = next((v for k, v in COMPONENT_KNOWLEDGE_BASE.items() if k in part_q), None)
        if found:
            st.success(f"Found: {part_q.upper()}")
            st.session_state.found_component = {"part_number": part_q.upper(), **found}
        else:
            st.warning("Not in DB. Research with these links:")
            if part_q:
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f"[Octopart](https://octopart.com/search?q={part_q})")
                with c2: st.markdown(f"[Digi-Key](https://www.digikey.com/en/products/result?s={part_q})")
                with c3: st.markdown(f"[Mouser](https://www.mouser.com/Search/Refine?Keyword={part_q})")
                with c4: st.markdown(f"[Wikipedia](https://en.wikipedia.org/wiki/Special:Search?search={part_q})")
    st.markdown("---")
    d = st.session_state.get("found_component", {})
    with st.form("component_form", clear_on_submit=True):
        st.markdown("### Add Component to Database")
        pn = st.text_input("Part Number", value=d.get("part_number", ""))
        mfg = st.text_input("Manufacturer", value=d.get("manufacturer", ""))
        func = st.text_input("Function", value=d.get("function", ""))
        val1 = st.text_input("Voltage/Value", value=d.get("voltage", d.get("value", "")))
        notes = st.text_input("Notes (e.g., certifications)", "")
        if st.form_submit_button("Add Component"):
            if pn:
                new_row = pd.DataFrame([{"Part Number": pn, "Manufacturer": mfg, "Function": func, "Voltage/Value": val1, "Notes": notes}])
                if 'component_db' not in st.session_state: st.session_state.component_db = pd.DataFrame()
                st.session_state.component_db = pd.concat([st.session_state.component_db, new_row], ignore_index=True)
                st.success(f"Component '{pn}' added.")
    if 'component_db' in st.session_state and not st.session_state.component_db.empty:
        st.markdown("#### Component Database")
        st.dataframe(st.session_state.component_db)
    st.markdown('</div>', unsafe_allow_html=True)

# ============= Module: Dashboard =============
else:
    st.markdown('<div class="gem-panel">', unsafe_allow_html=True)
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of compliance progress.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", 0)
    c2.metric("Requirements Generated", 0)
    c3.metric("Components in DB", len(st.session_state.get("component_db", [])))
    st.markdown('</div>', unsafe_allow_html=True)
