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
from services.checkin_service import find_today_match, find_gt_appointments_for_checkin, kiosk_checkin
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
    """Validate SETS number format (10 digits)"""
    if not sets_num:
        return False, "SETS number is required"
    
    # Remove any spaces or dashes
    sets_num = sets_num.replace(" ", "").replace("-", "")
    
    # Check if it's 10 digits
    if not re.match(r'^\d{10}$', sets_num):
        return False, "SETS number must be exactly 10 digits"
    
    # TODO: Re-enable SETS number prefix check before production
    # if not sets_num.startswith('7'):
    #     return True, "Warning: SETS numbers typically start with 7. Please verify your number."
    
    return True, "Valid"

st.set_page_config(page_title="Kiosk Check-In", layout="wide", page_icon="🏥")

# Add role selector to sidebar
role_selector_sidebar()

# Add navigation in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📍 Quick Navigation")
    if st.button("🏠 Home Dashboard", use_container_width=True):
        st.switch_page("main_app.py")
    if st.button("👥 Staff Queue", use_container_width=True):
        st.switch_page("pages/2_Staff_Queue.py")
    
    st.markdown("---")
    st.markdown("### ℹ️ Kiosk Mode")
    st.info("This page simulates the self-service kiosk interface for patient check-in.")

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
        <h1>�️ Genetic Testing Check-In</h1>
        <p>Cuyahoga County Office of Child Support - Welcome! Please check in for your appointment</p>
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
                Example: 7000000000<br>
                <br>
                <strong>📋 Multiple Cases:</strong><br>
                If you have multiple cases (e.g., testing for different children), all your appointments will be shown. 
                Please select the specific appointment you're checking in for today.
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
                    matches = find_gt_appointments_for_checkin(engine, sets_number=sets_number.strip(), 
                                                                last_name=last_name.strip())
                    
                    if not matches:
                        st.markdown("""
                            <div class="error-card">
                                <strong>❌ No Eligible Appointment Found</strong>
                                <p>We could not find an appointment for check-in matching your information.</p>
                                <p style="margin-top: 15px;"><strong>Please note:</strong></p>
                                <ul>
                                    <li>You can check in starting on your appointment date</li>
                                    <li>You can check in up to 30 days after any appointment</li>
                                    <li>If you have multiple cases, all eligible appointments will be shown</li>
                                    <li>Verify your SETS Number and last name are correct</li>
                                    <li>Or contact the front desk for assistance</li>
                                </ul>
                            </div>
                        """, unsafe_allow_html=True)
                    elif len(matches) == 1:
                        m = matches[0]
                        try:
                            appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p on %B %d, %Y")
                        except:
                            appt_time = str(m["testing_datetime"])
                        
                        # Determine if already checked in
                        already_checked_in = m.get("current_status") == "CHECKED_IN"
                        
                        timing_status = m.get('timing_status', '')
                        timing_color = {'Past (within 30 days)': '#856404', 'Today': '#155724', 'Upcoming': '#0c5460'}.get(timing_status, '#666')
                        
                        st.markdown(f"""
                            <div class="appointment-card">
                                <h3 style="color: #667eea; margin-top: 0;">✓ Appointment Found</h3>
                                <p style="font-size: 1.2em; color: #764ba2;"><strong>{m.get('appointment_label', 'Appointment')}</strong></p>
                                <p style="font-size: 1.1em;"><strong>Scheduled:</strong> {appt_time}</p>
                                <p style="font-size: 1.0em; color: {timing_color};"><strong>⏰ Status:</strong> {timing_status}</p>
                                <p style="font-size: 1.1em;"><strong>Name:</strong> {m.get('first_name', '')} {m.get('last_name', '')}</p>
                                <p style="font-size: 1.1em;"><strong>SETS:</strong> {m.get('sets_number', '')}</p>
                                {f'<p style="color: orange;"><strong>⚠️ Status:</strong> Already Checked In</p>' if already_checked_in else ''}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if not already_checked_in:
                            col1, col2, col3 = st.columns([1, 1, 1])
                            with col2:
                                if st.button("✅ Confirm Check-In", use_container_width=True, type="primary", key="confirm_single"):
                                    checkin_result = kiosk_checkin(engine, m["appointment_key"])
                                    st.session_state.checked_in = True
                                    
                                    # Build message with future appointments info
                                    message = f"You are checked in for your {m.get('appointment_label', 'appointment')} scheduled for {appt_time}."
                                    if checkin_result.get('future_appointments_count', 0) > 0:
                                        message += f"\\n\\nNote: You have {checkin_result['future_appointments_count']} future appointment(s) scheduled."
                                    
                                    st.session_state.checkin_message = message
                                    st.rerun()
                        else:
                            st.info("ℹ️ You have already checked in for this appointment. Please have a seat.")
                    else:
                        st.markdown("### 📋 Multiple Appointments Found")
                        st.info(f"""We found **{len(matches)} appointments** for you. 
                        This may include multiple cases or appointment dates. 
                        Please select the specific appointment you're checking in for:""")
                        
                        for i, m in enumerate(matches):
                            try:
                                appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p on %B %d, %Y")
                            except:
                                appt_time = str(m["testing_datetime"])
                            
                            already_checked_in = m.get("current_status") == "CHECKED_IN"
                            
                            timing_status = m.get('timing_status', '')
                            timing_color = {'Past (within 30 days)': '#856404', 'Today': '#155724', 'Upcoming': '#0c5460'}.get(timing_status, '#666')
                            
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.markdown(f"""
                                    <div class="appointment-card">
                                        <strong style="font-size: 1.2em; color: #764ba2;">{m.get('appointment_label', f'Appointment #{i+1}')}</strong>
                                        <p><strong>Scheduled:</strong> {appt_time}</p>
                                        <p style="color: {timing_color};"><strong>⏰ Status:</strong> {timing_status}</p>
                                        <p><strong>Assigned To:</strong> {m.get('assigned_to', 'N/A')}</p>
                                        {f'<p style="color: orange;"><strong>Status:</strong> Already Checked In</p>' if already_checked_in else ''}
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            with col2:
                                if not already_checked_in:
                                    if st.button("✅ Select", key=f"select_{i}", use_container_width=True, type="primary"):
                                        checkin_result = kiosk_checkin(engine, m["appointment_key"])
                                        st.session_state.checked_in = True
                                        
                                        message = f"You are checked in for your {m.get('appointment_label', 'appointment')} scheduled for {appt_time}."
                                        if checkin_result.get('future_appointments_count', 0) > 0:
                                            message += f"\n\nNote: You have {checkin_result['future_appointments_count']} future appointment(s) scheduled."
                                        
                                        st.session_state.checkin_message = message
                                        st.rerun()
                                else:
                                    st.markdown("<p style='text-align: center; color: orange;'>✓ Checked In</p>", unsafe_allow_html=True)
    
    # Check-in without SETS Number
    else:
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        st.markdown("### 👤 Check-In with Name Only")
        
        st.markdown("""
            <div class="help-box">
                <strong>ℹ️ Don't have your SETS number?</strong><br>
                No problem! You can check in using just your name.<br>
                <br>
                <strong>📋 Multiple Cases:</strong><br>
                If you have multiple cases (e.g., testing for different children), all your appointments will be shown. 
                Please select the specific appointment you're checking in for today.
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
                matches = find_gt_appointments_for_checkin(engine, first_name=first_name.strip(), 
                                                            last_name=last_name_alt.strip())
                
                if not matches:
                    st.markdown("""
                        <div class="error-card">
                            <strong>❌ No Eligible Appointment Found</strong>
                            <p>We could not find an appointment for check-in matching your name.</p>
                            <p style="margin-top: 15px;"><strong>Please note:</strong></p>
                            <ul>
                                <li>You can check in starting on your appointment date</li>
                                <li>You can check in up to 30 days after any appointment</li>
                                <li>If you have multiple cases, all eligible appointments will be shown</li>
                                <li>Verify your name is spelled correctly</li>
                                <li>Or contact the front desk for assistance</li>
                            </ul>
                        </div>
                    """, unsafe_allow_html=True)
                elif len(matches) == 1:
                    m = matches[0]
                    try:
                        appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p on %B %d, %Y")
                    except:
                        appt_time = str(m["testing_datetime"])
                    
                    already_checked_in = m.get("current_status") == "CHECKED_IN"
                    
                    timing_status = m.get('timing_status', '')
                    timing_color = {'Past (within 30 days)': '#856404', 'Today': '#155724', 'Upcoming': '#0c5460'}.get(timing_status, '#666')
                    
                    st.markdown(f"""
                        <div class="appointment-card">
                            <h3 style="color: #667eea; margin-top: 0;">✓ Appointment Found</h3>
                            <p style="font-size: 1.2em; color: #764ba2;"><strong>{m.get('appointment_label', 'Appointment')}</strong></p>
                            <p style="font-size: 1.1em;"><strong>Scheduled:</strong> {appt_time}</p>
                            <p style="font-size: 1.0em; color: {timing_color};"><strong>⏰ Status:</strong> {timing_status}</p>
                            <p style="font-size: 1.1em;"><strong>Name:</strong> {m.get('first_name', '')} {m.get('last_name', '')}</p>
                            <p style="font-size: 1.1em;"><strong>SETS:</strong> {m.get('sets_number', 'N/A')}</p>
                            {f'<p style="color: orange;"><strong>⚠️ Status:</strong> Already Checked In</p>' if already_checked_in else ''}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if not already_checked_in:
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col2:
                            if st.button("✅ Confirm Check-In", use_container_width=True, type="primary", key="confirm_single_alt"):
                                checkin_result = kiosk_checkin(engine, m["appointment_key"])
                                st.session_state.checked_in = True
                                
                                message = f"You are checked in for your {m.get('appointment_label', 'appointment')} scheduled for {appt_time}."
                                if checkin_result.get('future_appointments_count', 0) > 0:
                                    message += f"\n\nNote: You have {checkin_result['future_appointments_count']} future appointment(s) scheduled."
                                
                                st.session_state.checkin_message = message
                                st.rerun()
                    else:
                        st.info("ℹ️ You have already checked in for this appointment. Please have a seat.")
                else:
                    st.markdown("### 📋 Multiple Appointments Found")
                    st.info(f"""We found **{len(matches)} appointments** for you. 
                    This may include multiple cases or appointment dates. 
                    Please select the specific appointment you're checking in for:""")
                    
                    for i, m in enumerate(matches):
                        try:
                            appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p on %B %d, %Y")
                        except:
                            appt_time = str(m["testing_datetime"])
                        
                        already_checked_in = m.get("current_status") == "CHECKED_IN"
                        
                        timing_status = m.get('timing_status', '')
                        timing_color = {'Past (within 30 days)': '#856404', 'Today': '#155724', 'Upcoming': '#0c5460'}.get(timing_status, '#666')
                        
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"""
                                <div class="appointment-card">
                                    <strong style="font-size: 1.2em; color: #764ba2;">{m.get('appointment_label', f'Appointment #{i+1}')}</strong>
                                    <p><strong>Scheduled:</strong> {appt_time}</p>
                                    <p style="color: {timing_color};"><strong>⏰ Status:</strong> {timing_status}</p>
                                    <p><strong>SETS:</strong> {m.get('sets_number', 'N/A')}</p>
                                    {f'<p style="color: orange;"><strong>Status:</strong> Already Checked In</p>' if already_checked_in else ''}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if not already_checked_in:
                                if st.button("✅ Select", key=f"select_alt_{i}", use_container_width=True, type="primary"):
                                    checkin_result = kiosk_checkin(engine, m["appointment_key"])
                                    st.session_state.checked_in = True
                                    
                                    message = f"You are checked in for your {m.get('appointment_label', 'appointment')} scheduled for {appt_time}."
                                    if checkin_result.get('future_appointments_count', 0) > 0:
                                        message += f"\n\nNote: You have {checkin_result['future_appointments_count']} future appointment(s) scheduled."
                                    
                                    st.session_state.checkin_message = message
                                    st.rerun()
                            else:
                                st.markdown("<p style='text-align: center; color: orange;'>✓ Checked In</p>", unsafe_allow_html=True)
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
