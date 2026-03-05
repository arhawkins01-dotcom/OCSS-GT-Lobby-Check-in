"""
3_Admin_Export_Load.py
----------------------
Admin page for:
  1. Loading appointment data from an OnBase CSV export.
  2. Exporting check-in records for a date range.
Requires 'admin' role.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from services.appointment_service import bulk_upsert_appointments
from services.checkin_service import get_all_checkins_for_date
from utils.auth_utils import render_login_form, require_role
from utils.file_utils import build_export_dataframe, parse_onbase_export, records_to_csv_bytes
from utils.validation_utils import validate_appointment_records

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Admin Export & Load – OCSS Lobby",
    page_icon="⚙️",
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
st.title("⚙️ Admin – Export & Load Appointments")
st.markdown("---")

tab_load, tab_export = st.tabs(["📥 Load Appointments from OnBase", "📤 Export Check-In Records"])

# ===========================================================================
# Tab 1 – Load Appointments
# ===========================================================================
with tab_load:
    st.subheader("Upload OnBase Appointment Export")
    st.markdown(
        "Download today's (or a future day's) appointment list from OnBase as a CSV file "
        "and upload it here.  See `data/sample_onbase_export.csv` for the expected format."
    )

    uploaded_file = st.file_uploader(
        "Choose CSV file", type=["csv"], key="admin_upload_csv"
    )

    if uploaded_file is not None:
        raw_bytes = uploaded_file.read()
        records, parse_errors = parse_onbase_export(raw_bytes)

        if parse_errors:
            for err in parse_errors:
                st.error(err)
        else:
            valid_records, invalid_records = validate_appointment_records(records)

            st.markdown(f"**Total rows parsed:** {len(records)}")
            st.markdown(f"✅ Valid: {len(valid_records)} &nbsp; ❌ Invalid: {len(invalid_records)}")

            if invalid_records:
                with st.expander("Show invalid rows"):
                    st.dataframe(pd.DataFrame(invalid_records))

            if valid_records:
                with st.expander("Preview valid records", expanded=True):
                    st.dataframe(pd.DataFrame(valid_records))

                if st.button("💾 Load Valid Records into Database", use_container_width=True):
                    count = bulk_upsert_appointments(valid_records)
                    st.success(f"Successfully loaded {count} appointment record(s) into the database.")

# ===========================================================================
# Tab 2 – Export Check-In Records
# ===========================================================================
with tab_export:
    st.subheader("Export Check-In Records")
    st.markdown("Download check-in records for a specific date as a CSV file.")

    export_date = st.date_input(
        "Select date",
        value=date.today(),
        key="admin_export_date",
    )

    if st.button("📊 Load Records", use_container_width=True):
        records = get_all_checkins_for_date(export_date)
        if not records:
            st.info(f"No check-in records found for {export_date.isoformat()}.")
        else:
            df = build_export_dataframe(records)
            st.dataframe(df, use_container_width=True)

            csv_bytes = records_to_csv_bytes(records)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_bytes,
                file_name=f"OCSS_Export_{export_date.isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
