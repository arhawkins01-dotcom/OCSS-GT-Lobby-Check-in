"""
Admin page for the OCSS GT Lobby Check-In application.

Sections
--------
1. Load Export    — Upload the OnBase appointment export CSV
2. Appointment Overview — Full status table
3. No-Show Flagging     — Mark Scheduled patients as candidate No-Shows
4. Finalize No-Shows    — Admin confirms all flagged no-shows
5. OnBase Sync-Back     — Download / drop sync-back CSV to OUTBOX
"""

import os

import streamlit as st

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.state import (  # noqa: E402
    init_state,
    get_appointments,
    load_appointments,
    flag_no_show,
    unflag_no_show,
    finalize_no_shows,
)
from utils.onbase import parse_export, generate_syncback_bytes, write_syncback_to_outbox

# Path to OUTBOX directory (relative to repo root)
_OUTBOX_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "outbox"
)


def render() -> None:
    st.title("🔧 Admin Panel")

    init_state(st)

    # ── 1. Load Export ───────────────────────────────────────────────────────
    st.header("1. Load OnBase Export")
    uploaded = st.file_uploader(
        "Upload today's OnBase appointment export (CSV)",
        type=["csv"],
        key="onbase_upload",
    )
    if uploaded is not None:
        try:
            records = parse_export(uploaded)
            load_appointments(st, records)
            st.success(f"✅ Loaded {len(records)} appointment(s) from **{uploaded.name}**.")
        except ValueError as exc:
            st.error(f"❌ Could not parse CSV: {exc}")
        except Exception as exc:
            st.error(f"❌ Unexpected error reading file: {exc}")

    if not st.session_state.get("export_loaded"):
        st.info("No data loaded yet. Upload a CSV above to get started.")
        return

    appointments = get_appointments(st)

    # ── 2. Appointment Overview ──────────────────────────────────────────────
    st.header("2. Appointment Overview")

    status_order = ["Scheduled", "Checked-In", "In-Progress", "Completed", "No-Show-Pending", "No-Show"]
    status_emoji = {
        "Scheduled": "📅",
        "Checked-In": "✅",
        "In-Progress": "🔄",
        "Completed": "🏁",
        "No-Show-Pending": "⚠️",
        "No-Show": "❌",
    }

    import pandas as pd

    df = pd.DataFrame(appointments)
    display_df = df[["sets_number", "last_name", "first_name", "appt_datetime", "appt_type", "status"]].copy()
    display_df["status"] = display_df["status"].apply(
        lambda s: f"{status_emoji.get(s, '')} {s}"
    )
    display_df.columns = ["SETS #", "Last Name", "First Name", "Appt Date/Time", "Type", "Status"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── 3. No-Show Flagging ──────────────────────────────────────────────────
    st.header("3. Flag No-Shows")
    st.markdown(
        "Mark **Scheduled** patients who have not arrived as candidate No-Shows. "
        "These are not finalised until you click **Finalize** below."
    )

    scheduled = [a for a in appointments if a["status"] == "Scheduled"]
    pending = [a for a in appointments if a["status"] == "No-Show-Pending"]

    if scheduled or pending:
        col_headers = st.columns([3, 2, 2, 2])
        col_headers[0].markdown("**Patient**")
        col_headers[1].markdown("**Appt Time**")
        col_headers[2].markdown("**Type**")
        col_headers[3].markdown("**Action**")

        for appt in scheduled:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.write(f"{appt['first_name']} {appt['last_name'].title()} (SETS: {appt['sets_number']})")
            c2.write(appt["appt_datetime"])
            c3.write(appt["appt_type"])
            if c4.button("Flag No-Show", key=f"flag_{appt['sets_number']}"):
                flag_no_show(st, appt["sets_number"])
                st.rerun()

        for appt in pending:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.write(
                f"⚠️ {appt['first_name']} {appt['last_name'].title()} (SETS: {appt['sets_number']})"
            )
            c2.write(appt["appt_datetime"])
            c3.write(appt["appt_type"])
            if c4.button("↩ Undo Flag", key=f"unflag_{appt['sets_number']}"):
                unflag_no_show(st, appt["sets_number"])
                st.rerun()
    else:
        st.info("No Scheduled or flagged patients to display.")

    # ── 4. Finalize No-Shows ─────────────────────────────────────────────────
    st.header("4. Finalize No-Shows")
    pending_count = sum(1 for a in appointments if a["status"] == "No-Show-Pending")
    if pending_count:
        st.warning(
            f"There are **{pending_count}** flagged No-Show candidates. "
            "Finalizing will permanently mark them as No-Show."
        )
        if st.button("⚠️ Finalize No-Shows", type="primary"):
            count = finalize_no_shows(st)
            st.success(f"✅ {count} appointment(s) finalized as No-Show.")
            st.rerun()
    else:
        st.info("No pending No-Show flags to finalize.")

    # ── 5. OnBase Sync-Back ──────────────────────────────────────────────────
    st.header("5. Generate OnBase Sync-Back File")
    st.markdown(
        "Generates a CSV with updated appointment statuses for re-import into OnBase (Method A: CSV Drop to OUTBOX)."
    )

    col_dl, col_out = st.columns(2)

    with col_dl:
        csv_bytes = generate_syncback_bytes(appointments)
        st.download_button(
            label="⬇️ Download Sync-Back CSV",
            data=csv_bytes,
            file_name="onbase_syncback.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_out:
        if st.button("📤 Drop to OUTBOX", use_container_width=True):
            try:
                outbox_path = os.path.abspath(_OUTBOX_DIR)
                filepath = write_syncback_to_outbox(appointments, outbox_path)
                st.success(f"✅ Written to OUTBOX: `{os.path.basename(filepath)}`")
            except Exception as exc:
                st.error(f"❌ Failed to write OUTBOX file: {exc}")
