"""
1_Kiosk_CheckIn.py
------------------
Student self-service check-in kiosk page.
This page is public (no authentication required).
"""

import time
from datetime import date

import streamlit as st

from services.database_service import init_db
from services.appointment_service import find_appointments
from services.checkin_service import create_checkin
from utils.validation_utils import is_valid_gt_id, normalise_gt_id, is_valid_name

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OCSS GT Lobby Check-In",
    page_icon="🏛️",
    layout="centered",
)

# Ensure database is initialised on first load
init_db()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "kiosk_step" not in st.session_state:
    st.session_state.kiosk_step = "search"          # search | confirm | success | not_found
if "kiosk_matches" not in st.session_state:
    st.session_state.kiosk_matches = []
if "kiosk_selected_appt" not in st.session_state:
    st.session_state.kiosk_selected_appt = None
if "kiosk_last_activity" not in st.session_state:
    st.session_state.kiosk_last_activity = time.time()

# ---------------------------------------------------------------------------
# Auto-reset after inactivity
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 60
elapsed = time.time() - st.session_state.kiosk_last_activity
if elapsed > TIMEOUT_SECONDS and st.session_state.kiosk_step != "search":
    st.session_state.kiosk_step = "search"
    st.session_state.kiosk_matches = []
    st.session_state.kiosk_selected_appt = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏛️ OCSS GT Lobby Check-In")
st.markdown("---")

# ---------------------------------------------------------------------------
# Step 1 – Search
# ---------------------------------------------------------------------------
if st.session_state.kiosk_step == "search":
    st.subheader("Welcome! Please check in for your appointment.")
    st.markdown("Enter your **GT ID** *or* your **first and last name** below.")

    search_type = st.radio(
        "Search by:",
        options=["GT ID", "Name"],
        horizontal=True,
        key="kiosk_search_type",
    )

    gt_id = ""
    first_name = ""
    last_name = ""

    if search_type == "GT ID":
        gt_id = st.text_input("GT ID (e.g. gt123456)", key="kiosk_gt_id_input")
    else:
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name", key="kiosk_first_name")
        with col2:
            last_name = st.text_input("Last Name", key="kiosk_last_name")

    if st.button("🔍 Find My Appointment", use_container_width=True):
        st.session_state.kiosk_last_activity = time.time()
        today = date.today()

        if search_type == "GT ID":
            if not gt_id.strip():
                st.warning("Please enter your GT ID.")
                st.stop()
            if not is_valid_gt_id(gt_id):
                st.error("Invalid GT ID format. Please enter a valid GT ID (e.g. gt123456).")
                st.stop()
            matches = find_appointments(gt_id=normalise_gt_id(gt_id), appt_date=today)
        else:
            if not first_name.strip() or not last_name.strip():
                st.warning("Please enter both your first and last name.")
                st.stop()
            if not is_valid_name(first_name) or not is_valid_name(last_name):
                st.error("Please enter a valid name (letters only).")
                st.stop()
            matches = find_appointments(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                appt_date=today,
            )

        if matches:
            st.session_state.kiosk_matches = matches
            st.session_state.kiosk_step = "confirm"
            st.rerun()
        else:
            st.session_state.kiosk_step = "not_found"
            st.rerun()

# ---------------------------------------------------------------------------
# Step 2 – Confirm appointment
# ---------------------------------------------------------------------------
elif st.session_state.kiosk_step == "confirm":
    st.subheader("Please confirm your appointment")
    matches = st.session_state.kiosk_matches

    if len(matches) == 1:
        appt = matches[0]
        st.info(
            f"**{appt['student_first_name']} {appt['student_last_name']}**  \n"
            f"Appointment: {appt['appointment_type']}  \n"
            f"Time: {appt['appointment_time']}  \n"
            f"Counselor: {appt.get('counselor', 'N/A')}"
        )
        st.session_state.kiosk_selected_appt = appt
    else:
        st.write("Multiple appointments found. Please select yours:")
        options = {
            f"{a['appointment_time']} – {a['appointment_type']} with {a.get('counselor', 'N/A')}": a
            for a in matches
        }
        choice = st.selectbox("Select appointment", list(options.keys()), key="kiosk_appt_choice")
        st.session_state.kiosk_selected_appt = options[choice]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, Check Me In", use_container_width=True):
            st.session_state.kiosk_last_activity = time.time()
            appt = st.session_state.kiosk_selected_appt
            try:
                create_checkin(appt["appointment_id"], appt["student_gt_id"])
                st.session_state.kiosk_step = "success"
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with col2:
        if st.button("🔙 Start Over", use_container_width=True):
            st.session_state.kiosk_step = "search"
            st.session_state.kiosk_matches = []
            st.session_state.kiosk_selected_appt = None
            st.rerun()

# ---------------------------------------------------------------------------
# Step 3 – Success
# ---------------------------------------------------------------------------
elif st.session_state.kiosk_step == "success":
    appt = st.session_state.kiosk_selected_appt
    st.success(
        f"✅ You're checked in, **{appt['student_first_name']}**!  \n\n"
        f"Please have a seat. A staff member will be with you shortly."
    )
    st.balloons()

    if st.button("🔙 Return to Start", use_container_width=True):
        st.session_state.kiosk_step = "search"
        st.session_state.kiosk_matches = []
        st.session_state.kiosk_selected_appt = None
        st.rerun()

    # Auto-reset after 10 seconds
    time.sleep(10)
    st.session_state.kiosk_step = "search"
    st.session_state.kiosk_matches = []
    st.session_state.kiosk_selected_appt = None
    st.rerun()

# ---------------------------------------------------------------------------
# Step 4 – Not found
# ---------------------------------------------------------------------------
elif st.session_state.kiosk_step == "not_found":
    st.error(
        "⚠️ No appointment found for today.  \n\n"
        "Please speak with a front-desk staff member for assistance."
    )
    if st.button("🔙 Try Again", use_container_width=True):
        st.session_state.kiosk_step = "search"
        st.rerun()
