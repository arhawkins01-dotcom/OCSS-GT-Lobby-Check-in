"""
Staff Queue page for the OCSS GT Lobby Check-In application.

Shows two live queues:
  • Waiting      — patients with status CHECKED_IN (Start button)
  • In-Progress  — patients with status IN_PROCESS  (Complete button)
"""

import streamlit as st

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.state import (  # noqa: E402
    init_state,
    get_appointments,
    start_appointment,
    complete_appointment,
    STATUS_CHECKED_IN,
    STATUS_IN_PROCESS,
    STATUS_COMPLETED,
)


def render() -> None:
    st.title("📋 Staff Queue View")

    init_state(st)

    if not st.session_state.get("export_loaded"):
        st.warning("⚠️ No appointment data loaded. Please use the Admin panel to load today's schedule.")
        return

    appointments = get_appointments(st)

    waiting = [a for a in appointments if a["final_status"] == STATUS_CHECKED_IN]
    in_progress = [a for a in appointments if a["final_status"] == STATUS_IN_PROCESS]
    completed = [a for a in appointments if a["final_status"] == STATUS_COMPLETED]

    # ── Waiting queue ────────────────────────────────────────────────────────
    st.subheader(f"⏳ Waiting — {len(waiting)} patient(s)")
    if waiting:
        for appt in waiting:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(
                    f"**SETS: {appt['sets_number']}**  \n"
                    f"Appt: {appt['testing_datetime']}  \n"
                    f"Checked in: {appt['checkin_time'] or '—'}"
                )
            with col2:
                st.write(f"Key: `{appt['appointment_key']}`")
            with col3:
                if st.button("▶ Start", key=f"start_{appt['sets_number']}"):
                    start_appointment(st, appt["sets_number"])
                    st.rerun()
    else:
        st.info("No patients currently waiting.")

    st.divider()

    # ── In-Progress ──────────────────────────────────────────────────────────
    st.subheader(f"🔄 In-Process — {len(in_progress)} patient(s)")
    if in_progress:
        for appt in in_progress:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(
                    f"**SETS: {appt['sets_number']}**  \n"
                    f"Appt: {appt['testing_datetime']}  \n"
                    f"Started: {appt['in_process_time'] or '—'}"
                )
            with col2:
                st.write(f"Key: `{appt['appointment_key']}`")
            with col3:
                if st.button("✅ Complete", key=f"complete_{appt['sets_number']}"):
                    complete_appointment(st, appt["sets_number"])
                    st.rerun()
    else:
        st.info("No appointments currently in process.")

    st.divider()

    # ── Completed today ───────────────────────────────────────────────────────
    with st.expander(f"✔ Completed today — {len(completed)}", expanded=False):
        if completed:
            for appt in completed:
                st.write(
                    f"**SETS: {appt['sets_number']}** "
                    f"({appt['testing_datetime']}) — completed {appt['completed_time'] or '—'}"
                )
        else:
            st.write("None yet.")

    # ── Refresh ───────────────────────────────────────────────────────────────
    st.caption("Click Refresh to update the queue.")
    if st.button("🔄 Refresh now"):
        st.rerun()
