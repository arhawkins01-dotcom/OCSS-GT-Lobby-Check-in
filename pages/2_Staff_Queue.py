"""
2_Staff_Queue.py
----------------
Real-time view of the check-in queue for front-desk staff.
Requires 'staff' or 'admin' role.
"""

import time
from datetime import date

import streamlit as st

from services.checkin_service import get_active_queue, update_checkin_status
from utils.auth_utils import render_login_form, require_role, get_current_user

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Staff Queue – OCSS Lobby",
    page_icon="📋",
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
st.title("📋 Staff Check-In Queue")
st.markdown(f"**Date:** {date.today().strftime('%A, %B %d, %Y')}")
st.markdown("---")

# ---------------------------------------------------------------------------
# Auto-refresh control
# ---------------------------------------------------------------------------
REFRESH_SECONDS = 30
if "queue_last_refresh" not in st.session_state:
    st.session_state.queue_last_refresh = time.time()

col_title, col_refresh = st.columns([4, 1])
with col_refresh:
    if st.button("🔄 Refresh Now"):
        st.session_state.queue_last_refresh = time.time()
        st.rerun()

# ---------------------------------------------------------------------------
# Load queue
# ---------------------------------------------------------------------------
queue = get_active_queue(date.today())

if not queue:
    st.info("No students currently waiting.")
else:
    st.markdown(f"**{len(queue)} student(s) in queue**")
    st.markdown("---")

    for i, record in enumerate(queue):
        checkin_time = record.get("checkin_timestamp", "")
        if checkin_time:
            try:
                from datetime import datetime
                ct = datetime.fromisoformat(checkin_time)
                wait_minutes = int((datetime.now() - ct).total_seconds() / 60)
                wait_str = f"{wait_minutes} min"
            except Exception:
                wait_str = "—"
        else:
            wait_str = "—"

        status = record.get("checkin_status", "Waiting")
        status_emoji = "⏳" if status == "Waiting" else "🟢"

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 3])
            with col1:
                st.markdown(
                    f"**{record['student_first_name']} {record['student_last_name']}**  \n"
                    f"GT ID: `{record['student_gt_id']}`"
                )
            with col2:
                st.markdown(f"⏰ {record.get('appointment_time', '—')}")
            with col3:
                st.markdown(f"📁 {record.get('appointment_type', '—')}")
            with col4:
                st.markdown(f"👤 {record.get('counselor', '—')}")
                st.markdown(f"⌛ Wait: {wait_str}")
            with col5:
                if status == "Waiting":
                    if st.button(
                        "▶️ Mark In-Progress",
                        key=f"inprogress_{record['checkin_id']}",
                        use_container_width=True,
                    ):
                        update_checkin_status(record["checkin_id"], "In-Progress")
                        st.rerun()
                elif status == "In-Progress":
                    if st.button(
                        "✅ Mark Completed",
                        key=f"complete_{record['checkin_id']}",
                        use_container_width=True,
                    ):
                        update_checkin_status(record["checkin_id"], "Completed")
                        st.rerun()
                st.markdown(f"{status_emoji} **{status}**")

        st.divider()

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
elapsed = time.time() - st.session_state.queue_last_refresh
if elapsed >= REFRESH_SECONDS:
    st.session_state.queue_last_refresh = time.time()
    time.sleep(0.5)
    st.rerun()
