from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import yaml
import re
from datetime import datetime, date
from sqlalchemy import text
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.checkin_service import find_today_match, kiosk_checkin
from utils.auth_utils import get_user_role, role_selector_sidebar

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "app_config.yaml"

def get_engine():
    cfg = yaml.safe_load(open(CONFIG_PATH,"r",encoding="utf-8"))
    db_cfg = cfg["storage"]["db"]
    dbc = DBConfig(db_type=db_cfg.get("type","sqlite"),
                   sqlite_path=db_cfg.get("sqlite_path"),
                   sqlserver_connection_string=db_cfg.get("sqlserver_connection_string"))
    engine = build_engine(dbc)
    if dbc.db_type.lower()=="sqlite":
        init_sqlite_schema(engine)
    return engine

def validate_sets_number(sets_num):
    """Validate SETS number format (10 digits, usually starting with 7)"""
    if not sets_num:
        return False, "SETS number is required"
    
    # Remove any spaces or dashes
    sets_num = sets_num.replace(" ", "").replace("-", "")
    
    # Check if it's 10 digits
    if not re.match(r'^\d{10}$', sets_num):
        return False, "SETS number must be exactly 10 digits"
    
    # Warn if doesn't start with 7 (but still allow it)
    if not sets_num.startswith('7'):
        return True, "Warning: SETS numbers typically start with 7. Please verify your number."
    
    return True, "Valid"

def find_by_name(engine, first_name, last_name):
    """Find appointments by name only"""
    today = date.today().strftime("%Y-%m-%d")
    q = text("""
    SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.last_name, a.first_name,
           a.status_from_onbase, a.part_type, a.assigned_to, v.current_status
    FROM gt_appointments a
    JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
    WHERE substr(a.testing_datetime,1,10) = :day
      AND LOWER(a.first_name) = LOWER(:first_name)
      AND LOWER(a.last_name) = LOWER(:last_name)
    """)
    
    with engine.begin() as conn:
        rows = conn.execute(q, {"day": today, "first_name": first_name.strip(), "last_name": last_name.strip()}).mappings().all()
    
    return [dict(r) for r in rows]

st.set_page_config(page_title="Kiosk Check-In", layout="wide", page_icon="🏥")

# Add role selector to sidebar
role_selector_sidebar()

role = get_user_role()
if role != "kiosk":
    st.warning("⚠️ Kiosk page - Change role to 'kiosk' in sidebar to use this page.")

# Initialize session state
if "checked_in" not in st.session_state:
    st.session_state.checked_in = False
if "checkin_message" not in st.session_state:
    st.session_state.checkin_message = ""
if "checkin_method" not in st.session_state:
    st.session_state.checkin_method = "sets"

# Custom CSS for styling
st.markdown("""
    <style>
    .kiosk-header {
        text-align: center;
        padding: 30px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .kiosk-header h1 {
        margin: 0;
        font-size: 3em;
    }
    .kiosk-header p {
        margin: 15px 0 0 0;
        font-size: 1.3em;
    }
    .appointment-card {
        background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
        padding: 25px;
        border-radius: 12px;
        margin: 15px 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .success-card {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 3px solid #28a745;
        padding: 40px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(40,167,69,0.3);
    }
    .error-card {
        background: #f8d7da;
        border: 2px solid #dc3545;
        padding: 25px;
        border-radius: 12px;
    }
    .warning-card {
        background: #fff3cd;
        border: 2px solid #ffc107;
        padding: 20px;
        border-radius: 12px;
    }
    .input-section {
        background: white;
        padding: 35px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    .help-box {
        background: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="kiosk-header">
        <h1>🏥 Genetic Testing Check-In</h1>
        <p>Welcome! Please check in for your appointment</p>
    </div>
""", unsafe_allow_html=True)

# Show success message if checked in
if st.session_state.checked_in:
    st.markdown(f"""
        <div class="success-card">
            <h1 style="color: #28a745; margin: 0;">✅ Check-In Successful!</h1>
            <p style="font-size: 1.4em; margin: 25px 0; font-weight: 500;">
                {st.session_state.checkin_message}
            </p>
            <p style="color: #155724; margin-top: 30px; font-size: 1.1em;">
                Please have a seat in the waiting area.<br>A staff member will call you shortly.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✨ Check In Another Patient", use_container_width=True, type="primary", key="new_checkin"):
            st.session_state.checked_in = False
            st.session_state.checkin_message = ""
            st.rerun()
else:
    # Check-in method selection
    st.markdown("### 📋 Select Check-In Method")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔢 I Have My SETS Number", use_container_width=True, 
                     type="primary" if st.session_state.checkin_method == "sets" else "secondary"):
            st.session_state.checkin_method = "sets"
            st.rerun()
    
    with col2:
        if st.button("👤 I Don't Have My SETS Number", use_container_width=True,
                     type="primary" if st.session_state.checkin_method == "name" else "secondary"):
            st.session_state.checkin_method = "name"
            st.rerun()
    
    st.markdown("---")
    
    # Check-in with SETS Number
    if st.session_state.checkin_method == "sets":
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        st.markdown("### 🔢 Check-In with SETS Number")
        
        st.markdown("""
            <div class="help-box">
                <strong>ℹ️ About SETS Numbers:</strong><br>
                Your SETS number is a 10-digit identifier, usually starting with the number 7.<br>
                Example: 7000000000
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            sets_number = st.text_input(
                "SETS Number",
                placeholder="Enter 10-digit SETS Number",
                max_chars=10,
                help="Your unique SETS identification number (10 digits)",
                key="sets_input"
            )
            
            # Validate SETS number in real-time
            if sets_number:
                is_valid, message = validate_sets_number(sets_number)
                if not is_valid:
                    st.error(f"❌ {message}")
                elif "Warning" in message:
                    st.warning(f"⚠️ {message}")
                else:
                    st.success("✓ Valid SETS number format")
        
        with col2:
            last_name = st.text_input(
                "Last Name",
                placeholder="Enter your last name",
                help="Your last name as it appears in our system",
                key="sets_lastname"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Find appointment button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            find_button = st.button("🔍 Find My Appointment", use_container_width=True, type="primary", key="find_sets")
        
        if find_button:
            if not sets_number or not last_name:
                st.markdown("""
                    <div class="error-card">
                        <strong>⚠️ Missing Information</strong>
                        <p>Please enter both your SETS Number and Last Name.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                is_valid, message = validate_sets_number(sets_number)
                if not is_valid:
                    st.markdown(f"""
                        <div class="error-card">
                            <strong>❌ Invalid SETS Number</strong>
                            <p>{message}</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    engine = get_engine()
                    matches = find_today_match(engine, sets_number.strip(), last_name.strip())
                    matches = [m for m in matches if str(m.get("status_from_onbase","")).lower() not in ["cancelled","canceled"]]
                    
                    if not matches:
                        st.markdown("""
                            <div class="error-card">
                                <strong>❌ No Appointment Found</strong>
                                <p>We could not find an appointment matching your information for today.</p>
                                <p style="margin-top: 15px;"><strong>Please:</strong></p>
                                <ul>
                                    <li>Verify your SETS Number and last name are correct</li>
                                    <li>Or try the "I Don't Have My SETS Number" option above</li>
                                    <li>Or contact the front desk for assistance</li>
                                </ul>
                            </div>
                        """, unsafe_allow_html=True)
                    elif len(matches) == 1:
                        m = matches[0]
                        try:
                            appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p")
                        except:
                            appt_time = str(m["testing_datetime"])
                        
                        st.markdown(f"""
                            <div class="appointment-card">
                                <h3 style="color: #667eea; margin-top: 0;">✓ Appointment Found</h3>
                                <p style="font-size: 1.1em;"><strong>Time:</strong> {appt_time}</p>
                                <p style="font-size: 1.1em;"><strong>Name:</strong> {m.get('first_name', '')} {m.get('last_name', '')}</p>
                                <p style="font-size: 1.1em;"><strong>SETS:</strong> {m.get('sets_number', '')}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col2:
                            if st.button("✅ Confirm Check-In", use_container_width=True, type="primary", key="confirm_single"):
                                kiosk_checkin(engine, m["appointment_key"])
                                st.session_state.checked_in = True
                                st.session_state.checkin_message = f"You are checked in for your {appt_time} appointment."
                                st.rerun()
                    else:
                        st.markdown("### 📋 Multiple Appointments Found")
                        st.info("We found multiple appointments for you today. Please select the correct one:")
                        
                        for i, m in enumerate(matches):
                            try:
                                appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p")
                            except:
                                appt_time = str(m["testing_datetime"])
                            
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.markdown(f"""
                                    <div class="appointment-card">
                                        <strong style="font-size: 1.1em;">Appointment #{i+1}</strong>
                                        <p><strong>Time:</strong> {appt_time}</p>
                                        <p><strong>Type:</strong> {m.get('part_type', 'Standard')}</p>
                                        <p><strong>Assigned To:</strong> {m.get('assigned_to', 'N/A')}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            with col2:
                                if st.button("✅ Select", key=f"select_{i}", use_container_width=True, type="primary"):
                                    kiosk_checkin(engine, m["appointment_key"])
                                    st.session_state.checked_in = True
                                    st.session_state.checkin_message = f"You are checked in for your {appt_time} appointment."
                                    st.rerun()
    
    # Check-in without SETS Number
    else:
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        st.markdown("### 👤 Check-In with Name Only")
        
        st.markdown("""
            <div class="help-box">
                <strong>ℹ️ Don't have your SETS number?</strong><br>
                No problem! You can check in using just your name.
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input(
                "First Name",
                placeholder="Enter your first name",
                key="name_firstname"
            )
        
        with col2:
            last_name_alt = st.text_input(
                "Last Name",
                placeholder="Enter your last name",
                key="name_lastname"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Find appointment button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            find_button_alt = st.button("🔍 Find My Appointment", use_container_width=True, type="primary", key="find_name")
        
        if find_button_alt:
            if not first_name or not last_name_alt:
                st.markdown("""
                    <div class="error-card">
                        <strong>⚠️ Missing Information</strong>
                        <p>Please enter both your first name and last name.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                engine = get_engine()
                matches = find_by_name(engine, first_name.strip(), last_name_alt.strip())
                matches = [m for m in matches if str(m.get("status_from_onbase","")).lower() not in ["cancelled","canceled"]]
                
                if not matches:
                    st.markdown("""
                        <div class="error-card">
                            <strong>❌ No Appointment Found</strong>
                            <p>We could not find an appointment matching your name for today.</p>
                            <p style="margin-top: 15px;">Please verify your name is spelled correctly or contact the front desk for assistance.</p>
                        </div>
                    """, unsafe_allow_html=True)
                elif len(matches) == 1:
                    m = matches[0]
                    try:
                        appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p")
                    except:
                        appt_time = str(m["testing_datetime"])
                    
                    st.markdown(f"""
                        <div class="appointment-card">
                            <h3 style="color: #667eea; margin-top: 0;">✓ Appointment Found</h3>
                            <p style="font-size: 1.1em;"><strong>Time:</strong> {appt_time}</p>
                            <p style="font-size: 1.1em;"><strong>Name:</strong> {m.get('first_name', '')} {m.get('last_name', '')}</p>
                            <p style="font-size: 1.1em;"><strong>SETS:</strong> {m.get('sets_number', 'N/A')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        if st.button("✅ Confirm Check-In", use_container_width=True, type="primary", key="confirm_single_alt"):
                            kiosk_checkin(engine, m["appointment_key"])
                            st.session_state.checked_in = True
                            st.session_state.checkin_message = f"You are checked in for your {appt_time} appointment."
                            st.rerun()
                else:
                    st.markdown("### 📋 Multiple Appointments Found")
                    st.info("We found multiple appointments for you today. Please select the correct one:")
                    
                    for i, m in enumerate(matches):
                        try:
                            appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p")
                        except:
                            appt_time = str(m["testing_datetime"])
                        
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"""
                                <div class="appointment-card">
                                    <strong style="font-size: 1.1em;">Appointment #{i+1}</strong>
                                    <p><strong>Time:</strong> {appt_time}</p>
                                    <p><strong>SETS:</strong> {m.get('sets_number', 'N/A')}</p>
                                    <p><strong>Type:</strong> {m.get('part_type', 'Standard')}</p>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if st.button("✅ Select", key=f"select_alt_{i}", use_container_width=True, type="primary"):
                                kiosk_checkin(engine, m["appointment_key"])
                                st.session_state.checked_in = True
                                st.session_state.checkin_message = f"You are checked in for your {appt_time} appointment."
                                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 30px;">
        <p style="font-size: 1.1em;"><strong>Need Help?</strong></p>
        <p>If you're having trouble checking in, please ask a staff member at the front desk.</p>
    </div>
""", unsafe_allow_html=True)
