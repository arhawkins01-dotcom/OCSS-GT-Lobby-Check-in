"""
Kiosk Check-In page for the OCSS GT Lobby Check-In application.

Patients enter their SETS Number and Last Name to check in.
The form validates against the appointments loaded from the OnBase export.
"""

import streamlit as st

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.state import init_state, check_in  # noqa: E402


def render() -> None:
    st.title("🏥 GT Lobby — Patient Check-In")

    init_state(st)

    if not st.session_state.get("export_loaded"):
        st.warning(
            "⚠️ No appointment data has been loaded yet. "
            "Please ask the front desk staff to load today's schedule in the **Admin** panel."
        )
        return

    st.markdown(
        "Please enter your **SETS Number** and **Last Name** exactly as they appear in your appointment letter."
    )

    with st.form("checkin_form", clear_on_submit=True):
        sets_number = st.text_input(
            "SETS Number",
            placeholder="e.g. 100001",
            max_chars=20,
        )
        last_name = st.text_input(
            "Last Name",
            placeholder="e.g. Smith",
            max_chars=60,
        )
        submitted = st.form_submit_button("Check In", use_container_width=True)

    if submitted:
        success, message = check_in(st, sets_number, last_name)
        if success:
            st.success(message)
            st.balloons()
        else:
            st.error(message)
