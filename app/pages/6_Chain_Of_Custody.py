import streamlit as st
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
import sys
import os

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.coc_service import create_coc_form, get_coc_form, update_coc_form_status
from services.related_party_service import get_related_parties
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

# Add role selector to sidebar
role_selector_sidebar()

st.set_page_config(page_title="Chain of Custody Form", page_icon="📋", layout="wide")

# Add navigation in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📍 Quick Navigation")
    if st.button("🏠 Home Dashboard", use_container_width=True):
        st.switch_page("main_app.py")
    if st.button("✅ Kiosk Check-In", use_container_width=True):
        st.switch_page("pages/1_Kiosk_CheckIn.py")
    if st.button("👥 Staff Queue", use_container_width=True):
        st.switch_page("pages/2_Staff_Queue.py")
    if st.button("📤 Export/Load", use_container_width=True):
        st.switch_page("pages/3_Admin_Export_Load.py")
    st.markdown("---")

role = get_user_role()
if role not in ['staff', 'admin']:
    st.warning("⚠️ This page requires staff or admin role.")
    st.stop()

st.title("📋 Chain of Custody Form Generator")
st.markdown("---")

# Get database engine
engine = get_engine()

# Get checked-in appointments for COC form generation
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.last_name, a.first_name,
               a.assigned_to, a.status_from_onbase, a.part_type, a.appointment_type, a.related_cases,
               v.current_status
        FROM gt_appointments a
        JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
        WHERE v.current_status = 'CHECKED_IN'
        ORDER BY a.testing_datetime DESC
    """))
    checked_in_appointments = [dict(row) for row in result]

if not checked_in_appointments:
    st.info("ℹ️ No checked-in appointments available. Customers must check in first before generating COC forms.")
    st.stop()

# Convert to list for selection
appointment_options = [
    f"{row['first_name']} {row['last_name']} - SETS: {row['sets_number'] or 'Name-Only'} - {row['testing_datetime']}" 
    for row in checked_in_appointments
]

st.subheader("Step 1: Select Appointment")
selected_idx = st.selectbox(
    "Choose appointment for COC form:",
    options=range(len(appointment_options)),
    format_func=lambda i: appointment_options[i]
)

selected_appt = checked_in_appointments[selected_idx]

# Display appointment information
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Customer Name", f"{selected_appt['first_name']} {selected_appt['last_name']}")
with col2:
    st.metric("SETS Number", selected_appt['sets_number'] or "Name-Only")
with col3:
    st.metric("Appointment Time", str(selected_appt['testing_datetime'])[:16])

st.markdown("---")
st.subheader("Step 2: Collector Information")

col1, col2 = st.columns(2)
with col1:
    collector_name = st.text_input(
        "Collector Name",
        value=st.session_state.get('user_name', ''),
        help="Name of staff member collecting the sample"
    )
    
with col2:
    collector_id = st.text_input(
        "Collector ID / Badge Number",
        help="Staff badge or ID number"
    )

st.markdown("---")
st.subheader("Step 3: Collection Details")

col1, col2 = st.columns(2)
with col1:
    collection_site = st.selectbox(
        "Collection Site",
        ["Cuyahoga County Office of Child Support", "Other - Specify Below"],
        help="Location where sample was collected"
    )
    if collection_site == "Other - Specify Below":
        collection_site = st.text_input("Specify Collection Site")

with col2:
    collection_date = st.date_input(
        "Collection Date",
        value=datetime.now(),
        help="Date sample was collected"
    )

collection_time = st.time_input(
    "Collection Time",
    value=datetime.now().time(),
    help="Time sample was collected"
)

st.markdown("---")
st.subheader("Step 4: Party Information")

# Primary customer/case party
with st.expander("📋 Customer/Case Party Information", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Full Name", value=f"{selected_appt['first_name']} {selected_appt['last_name']}", disabled=True)
    with col2:
        st.text_input("Case #/IV-D #", help="Case number or IV-D identification")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.date_input("Date of Birth", help="Customer date of birth")
    with col2:
        st.text_input("ID Type", placeholder="Driver's License, Passport, etc.")
    with col3:
        st.text_input("ID Number")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Race/Ethnicity", ["White", "Black/African American", "Hispanic/Latino", "Asian", "Native American", "Other", "Unknown"])
    with col2:
        st.text_input("Medical History Notes", help="Any relevant medical information")

# Related party context for staff use
with st.expander("🔗 Related Case Parties (Staff View)", expanded=False):
    related = get_related_parties(engine, selected_appt["appointment_key"])
    if not related:
        st.caption("No related parties found.")
    else:
        for party in related:
            st.write(
                f"- {party.get('party_name','Unknown')} | Role: {party.get('part_type','Unknown')} | "
                f"Status: {party.get('current_status','Unknown')} | Arrival: {party.get('arrival_status','UNKNOWN')}"
            )

# Additional party information (Mother, Child, Alleged Father)
with st.expander("👨‍👩‍👧 Additional Parties (Optional)"):
    st.write("**Mother Information**")
    col1, col2 = st.columns(2)
    with col1:
        mother_name = st.text_input("Mother Name")
    with col2:
        mother_dob = st.date_input("Mother DOB")
    
    st.write("**Child Information**")
    col1, col2 = st.columns(2)
    with col1:
        child_name = st.text_input("Child Name")
    with col2:
        child_dob = st.date_input("Child DOB")
    
    st.write("**Alleged Father Information (if applicable)**")
    col1, col2 = st.columns(2)
    with col1:
        af_name = st.text_input("Alleged Father Name")
    with col2:
        af_dob = st.date_input("Alleged Father DOB")

st.markdown("---")
st.subheader("Step 5: Collector's Statement")

collector_statement = st.text_area(
    "Collector's Statement",
    placeholder="Document the collection process and observations: sample type, container IDs, sealing method, any incidents or issues, witness information, etc.",
    height=150,
    help="Professional documentation of the collection process"
)

with st.expander("✏️ Collector's Affirmation"):
    st.checkbox("⚖️ I certify that I personally collected the above-identified sample(s) and that the seal(s) or other identifying devices on the above-listed package(s) have not been broken or tampered with.")
    witness_name = st.text_input("Witness Name (if applicable)")

st.markdown("---")
st.subheader("Step 6: Lab Section")

with st.expander("🧬 Sample & Lab Information"):
    col1, col2 = st.columns(2)
    with col1:
        sample_type = st.selectbox(
            "Sample Type",
            ["Buccal Swab", "Blood", "Saliva", "Other"],
            help="Type of genetic sample collected"
        )
    with col2:
        container_id = st.text_input("Container / Specimen ID", help="Lab container identification number")
    
    st.write("**Sample Sealing & Transport**")
    col1, col2 = st.columns(2)
    with col1:
        seal_verified = st.checkbox("✓ Seal verified intact and secure")
    with col2:
        lab_recipient = st.text_input("Received by (Lab Staff Name)")

notes = st.text_area(
    "Additional Notes",
    placeholder="Any additional information relevant to this COC form",
    height=100
)

st.markdown("---")

# Form submission buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Save as Draft", use_container_width=True, type="secondary"):
        try:
            coc_data = create_coc_form(
                engine=engine,
                appointment_key=selected_appt['appointment_key'],
                collector_name=collector_name,
                collector_id=collector_id,
                notes=f"Collection Site: {collection_site}\nCollection Time: {collection_date} {collection_time}\nStatement: {collector_statement}\n{notes}"
            )
            st.success(f"✅ COC Form saved as draft (ID: {coc_data['coc_id'][:8]}...)")
            st.session_state.last_coc_id = coc_data['coc_id']
        except Exception as e:
            st.error(f"❌ Error saving COC form: {str(e)}")

with col2:
    if st.button("✅ Complete & Save", use_container_width=True, type="primary"):
        if not collector_name or not collection_site:
            st.error("❌ Please fill in Collector Name and Collection Site")
        else:
            try:
                coc_data = create_coc_form(
                    engine=engine,
                    appointment_key=selected_appt['appointment_key'],
                    collector_name=collector_name,
                    collector_id=collector_id,
                    notes=f"Collection Site: {collection_site}\nCollection Time: {collection_date} {collection_time}\nStatement: {collector_statement}\n{notes}"
                )
                
                # Update status to COMPLETED
                update_coc_form_status(engine, coc_data['coc_id'], 'COMPLETED')
                
                st.success(f"✅ COC Form completed and saved (ID: {coc_data['coc_id'][:8]}...)")
                st.session_state.last_coc_id = coc_data['coc_id']
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error completing COC form: {str(e)}")

with col3:
    if st.button("📥 Preview PDF", use_container_width=True, type="secondary"):
        st.info("📄 PDF generation coming soon - will generate printable COC document")

st.markdown("---")

# Display recent COC forms
st.subheader("Recent COC Forms")
try:
    # Query recent COC forms from database
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT coc_id, appointment_key, collector_name, created_at, status
            FROM coc_forms
            ORDER BY created_at DESC
            LIMIT 5
        """))
        recent_forms = result.fetchall()
    
    if recent_forms:
        for form in recent_forms:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.caption(f"ID: {form[0][:8]}...")
            with col2:
                st.caption(f"Collector: {form[2]}")
            with col3:
                status_emoji = "📋" if form[4] == "DRAFT" else "✅" if form[4] == "COMPLETED" else "🖨️"
                st.caption(f"{status_emoji} {form[4]}")
            with col4:
                st.caption(form[3][:10] if form[3] else "N/A")
    else:
        st.info("No COC forms generated yet")
except Exception as e:
    st.warning(f"Could not load recent COC forms: {str(e)}")

st.markdown("---")
st.caption("💾 All data is securely stored in the database. COC forms are available for review and printing.")
