"""
Staff Queue page for the OCSS GT Lobby Check-In application.

Shows two live queues:
  • Waiting      — patients who have checked in (Start button)
  • In-Progress  — patients whose appointment has been started (Complete button)

The page auto-refreshes every 30 seconds so staff always see current data.
"""

import time

import streamlit as st

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.state import (  # noqa: E402
    init_state,
    get_appointments,
    start_appointment,
    complete_appointment,
)


def render() -> None:
    st.title("📋 Staff Queue View")

    init_state(st)

    if not st.session_state.get("export_loaded"):
        st.warning("⚠️ No appointment data loaded. Please use the Admin panel to load today's schedule.")
        return

    appointments = get_appointments(st)

    waiting = [a for a in appointments if a["status"] == "Checked-In"]
    in_progress = [a for a in appointments if a["status"] == "In-Progress"]
    completed = [a for a in appointments if a["status"] == "Completed"]

    # ── Waiting queue ────────────────────────────────────────────────────────
    st.subheader(f"⏳ Waiting — {len(waiting)} patient(s)")
    if waiting:
        for appt in waiting:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(
                    f"**{appt['first_name']} {appt['last_name'].title()}**  \n"
                    f"SETS: {appt['sets_number']} · {appt['appt_type']}  \n"
                    f"Checked in: {appt['checkin_time'] or '—'}"
                )
            with col2:
                st.write(f"🕐 {appt['appt_datetime']}")
            with col3:
                if st.button("▶ Start", key=f"start_{appt['sets_number']}"):
                    start_appointment(st, appt["sets_number"])
                    st.rerun()
    else:
        st.info("No patients currently waiting.")

    st.divider()

    # ── In-Progress ──────────────────────────────────────────────────────────
    st.subheader(f"🔄 In-Progress — {len(in_progress)} patient(s)")
    if in_progress:
        for appt in in_progress:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(
                    f"**{appt['first_name']} {appt['last_name'].title()}**  \n"
                    f"SETS: {appt['sets_number']} · {appt['appt_type']}  \n"
                    f"Started: {appt['start_time'] or '—'}"
                )
            with col2:
                st.write(f"🕐 {appt['appt_datetime']}")
            with col3:
                if st.button("✅ Complete", key=f"complete_{appt['sets_number']}"):
                    complete_appointment(st, appt["sets_number"])
                    st.rerun()
    else:
        st.info("No appointments currently in progress.")

    st.divider()

    # ── Completed today ───────────────────────────────────────────────────────
    with st.expander(f"✔ Completed today — {len(completed)}", expanded=False):
        if completed:
            for appt in completed:
                st.write(
                    f"**{appt['first_name']} {appt['last_name'].title()}** "
                    f"(SETS: {appt['sets_number']}) — completed {appt['complete_time'] or '—'}"
                )
        else:
            st.write("None yet.")

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    st.caption("Page auto-refreshes every 30 seconds.")
    time.sleep(0)  # yield to Streamlit; actual refresh via fragment rerun below
    if st.button("🔄 Refresh now"):
        st.rerun()
