from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import yaml
from datetime import datetime
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.checkin_service import find_today_match, kiosk_checkin
from utils.auth_utils import get_user_role

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "app_config.yaml"

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

st.set_page_config(page_title="Kiosk Check-In", layout="wide")
role = get_user_role()
if role != "kiosk":
    st.warning("Kiosk page (starter role gate).")

# Initialize session state
if "checked_in" not in st.session_state:
    st.session_state.checked_in = False
if "checkin_message" not in st.session_state:
    st.session_state.checkin_message = ""

# Custom CSS for styling
st.markdown("""
    <style>
    .kiosk-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 30px;
    }
    .kiosk-header h1 {
        margin: 0;
        font-size: 2.5em;
    }
    .kiosk-header p {
        margin: 10px 0 0 0;
        font-size: 1.1em;
    }
    .appointment-card {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #667eea;
    }
    .success-card {
        background: #d4edda;
        border: 2px solid #28a745;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
    }
    .error-card {
        background: #f8d7da;
        border: 2px solid #dc3545;
        padding: 20px;
        border-radius: 10px;
    }
    .input-section {
        background: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="kiosk-header">
        <h1>🏥 Genetic Testing Check-In</h1>
        <p>Welcome! Please enter your information to check in.</p>
    </div>
""", unsafe_allow_html=True)

# Show success message if checked in
if st.session_state.checked_in:
    st.markdown(f"""
        <div class="success-card">
            <h2>✅ Check-In Successful!</h2>
            <p style="font-size: 1.2em; margin: 20px 0;">
                {st.session_state.checkin_message}
            </p>
            <p style="color: #666; margin-top: 30px;">
                Please proceed to the reception area and check in with staff.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("Check in Another Patient", use_container_width=True):
            st.session_state.checked_in = False
            st.session_state.checkin_message = ""
            st.rerun()
else:
    # Main input form
    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Patient Information")
        sets_number = st.text_input(
            "SETS Number",
            placeholder="Enter your SETS Number",
            help="Your unique SETS identification number"
        )
    
    with col2:
        st.markdown("### Last Name")
        last_name = st.text_input(
            "Last Name",
            placeholder="Enter your last name",
            help="Your last name as it appears in our system"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Find and check-in buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        find_button = st.button("🔍 Find Appointment", use_container_width=True, type="primary", key="find_btn")
    
    if find_button:
        if not sets_number or not last_name:
            st.markdown("""
                <div class="error-card">
                    <strong>⚠️ Missing Information</strong>
                    <p>Please enter both your SETS Number and Last Name to find your appointment.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            engine = get_engine()
            matches = find_today_match(engine, sets_number, last_name)
            matches = [m for m in matches if str(m.get("status_from_onbase","")).lower() not in ["cancelled","canceled"]]
            
            if not matches:
                st.markdown("""
                    <div class="error-card">
                        <strong>❌ No Appointment Found</strong>
                        <p>We could not find an appointment for you today. Please check your SETS Number and last name, or contact the front desk for assistance.</p>
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
                        <strong>✓ Appointment Found</strong>
                        <p><strong>Time:</strong> {appt_time}</p>
                        <p><strong>Name:</strong> {m.get('first_name', '')} {m.get('last_name', '')}</p>
                        <p><strong>SETS:</strong> {m.get('sets_number', '')}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("✅ Confirm Check-In", use_container_width=True, type="primary", key="confirm_single"):
                        kiosk_checkin(engine, m["appointment_key"])
                        st.session_state.checked_in = True
                        st.session_state.checkin_message = f"You are checked in for {appt_time}. Please have a seat."
                        st.rerun()
            else:
                st.markdown("### Multiple Appointments Found")
                st.info("We found multiple appointments for you today. Please select the one you're checking in for:")
                
                # Display all matching appointments
                for i, m in enumerate(matches):
                    try:
                        appt_time = datetime.fromisoformat(str(m["testing_datetime"])).strftime("%I:%M %p")
                    except:
                        appt_time = str(m["testing_datetime"])
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                            <div class="appointment-card">
                                <strong>Appointment {i+1}</strong>
                                <p><strong>Time:</strong> {appt_time}</p>
                                <p><strong>Type:</strong> {m.get('appointment_type', 'Standard')}</p>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("Select", key=f"select_{i}"):
                            kiosk_checkin(engine, m["appointment_key"])
                            st.session_state.checked_in = True
                            st.session_state.checkin_message = f"You are checked in for {appt_time}. Please have a seat."
                            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 20px;">
        <p><small>If you need assistance, please ask a staff member at the front desk.</small></p>
    </div>
""", unsafe_allow_html=True)
