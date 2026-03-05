"""
5_Generate_OnBase_Sync_File.py
------------------------------
Generates the daily OnBase sync CSV file for a selected date.
Requires 'admin' role.
"""

from datetime import date
from pathlib import Path

import streamlit as st

from services.sync_service import build_sync_records, write_sync_file
from utils.auth_utils import get_current_user, render_login_form, require_role
from utils.file_utils import records_to_csv_bytes

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Generate OnBase Sync File – OCSS Lobby",
    page_icon="🔄",
    layout="wide",
)

render_login_form()

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
if not require_role("admin"):
    st.warning("🔒 Administrator access required.")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔄 Generate OnBase Sync File")
st.markdown("---")
st.markdown(
    "Select a date and generate the **OnBase sync CSV** that records appointment outcomes "
    "(check-in times, check-out times, and no-show flags).  "
    "Download the file and upload it to OnBase."
)

# ---------------------------------------------------------------------------
# Date selector
# ---------------------------------------------------------------------------
sync_date = st.date_input(
    "Select sync date",
    value=date.today(),
    key="sync_date",
)

# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
if st.button("🔍 Preview Sync Records"):
    records = build_sync_records(sync_date)
    if not records:
        st.info(f"No appointment records found for {sync_date.isoformat()}.")
    else:
        import pandas as pd
        st.success(f"Found **{len(records)}** record(s) for {sync_date.isoformat()}.")
        st.dataframe(pd.DataFrame(records), use_container_width=True)
        st.session_state["sync_preview_records"] = records

# ---------------------------------------------------------------------------
# Generate & Download
# ---------------------------------------------------------------------------
if "sync_preview_records" in st.session_state:
    records = st.session_state["sync_preview_records"]

    st.markdown("---")
    st.subheader("Download Sync File")

    csv_bytes = records_to_csv_bytes(records)
    from datetime import datetime
    filename = f"OCSS_GT_Sync_{sync_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.csv"

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        if st.button("💾 Save to Server & Log", use_container_width=True):
            user = get_current_user()
            generated_by = user["username"] if user else "admin"

            from services.sync_service import generate_sync_file
            file_path = generate_sync_file(sync_date, generated_by)
            st.success(f"Sync file saved: `{file_path.name}`")
