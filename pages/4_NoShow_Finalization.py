"""
4_NoShow_Finalization.py
------------------------
Allows staff/admin to finalize no-shows for a given appointment date.
Requires 'staff' or 'admin' role.
"""

from datetime import date

import pandas as pd
import streamlit as st

from services.appointment_service import get_appointments_for_date
from services.checkin_service import finalize_no_shows, get_all_checkins_for_date
from utils.auth_utils import get_current_user, render_login_form, require_role

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="No-Show Finalization – OCSS Lobby",
    page_icon="🚫",
    layout="wide",
)

render_login_form()

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
if not require_role("staff"):
    st.warning("🔒 Please log in as a staff member or administrator to access this page.")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🚫 No-Show Finalization")
st.markdown("---")
st.markdown(
    "Use this page to finalize **no-show** records for appointments where the student "
    "did not check in.  This action cannot be undone."
)

# ---------------------------------------------------------------------------
# Date selector
# ---------------------------------------------------------------------------
selected_date = st.date_input(
    "Select appointment date",
    value=date.today(),
    key="noshow_date",
)

if st.button("🔍 Review Appointments for this Date"):
    appointments = get_appointments_for_date(selected_date)
    checkins = get_all_checkins_for_date(selected_date)

    checked_in_appt_ids = {c["appointment_id"] for c in checkins if c.get("checkin_status") != "NoShow"}
    pending_noshows = [a for a in appointments if a["appointment_id"] not in checked_in_appt_ids]

    st.session_state["noshow_appointments"] = appointments
    st.session_state["noshow_pending"] = pending_noshows
    st.session_state["noshow_checkins"] = checkins

if "noshow_pending" in st.session_state:
    appointments = st.session_state["noshow_appointments"]
    pending_noshows = st.session_state["noshow_pending"]
    checkins = st.session_state["noshow_checkins"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Appointments", len(appointments))
    with col2:
        st.metric("Checked In", len(appointments) - len(pending_noshows))
    with col3:
        st.metric("Pending No-Shows", len(pending_noshows))

    st.markdown("---")

    if pending_noshows:
        st.subheader("Appointments Pending No-Show Finalization")
        df = pd.DataFrame(pending_noshows)[
            ["appointment_id", "student_gt_id", "student_first_name", "student_last_name",
             "appointment_time", "appointment_type", "counselor"]
        ]
        df.columns = ["Appt ID", "GT ID", "First Name", "Last Name", "Time", "Type", "Counselor"]
        st.dataframe(df, use_container_width=True)

        st.warning(
            f"⚠️ You are about to mark **{len(pending_noshows)}** appointment(s) as No-Show. "
            "This cannot be undone."
        )

        user = get_current_user()
        finalized_by = user["username"] if user else "system"

        if st.button(
            f"✅ Finalize {len(pending_noshows)} No-Show(s)",
            type="primary",
            use_container_width=True,
        ):
            count = finalize_no_shows(selected_date, finalized_by)
            st.success(f"Successfully finalized {count} no-show record(s) for {selected_date.isoformat()}.")
            # Clear session state to force refresh
            for key in ["noshow_appointments", "noshow_pending", "noshow_checkins"]:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.success("✅ All appointments for this date have been checked in or already finalized.")
