"""
Admin page for the OCSS GT Lobby Check-In application.

Sections
--------
1. Load Export          — Upload the OnBase appointment export CSV
2. Appointment Overview — Full status table with all OnBase columns
3. No-Show Flagging     — Mark SCHEDULED patients as candidate No-Shows
4. Finalize No-Shows    — Admin confirms all flagged no-shows
5. OnBase Sync-Back     — Download / drop GT_RESULTS_YYYYMMDD_HHMMSS.csv to OUTBOX
"""

import os

import pandas as pd
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
    STATUS_SCHEDULED,
    STATUS_CHECKED_IN,
    STATUS_IN_PROCESS,
    STATUS_COMPLETED,
    STATUS_NO_SHOW,
    STATUS_NO_SHOW_PENDING,
)
from utils.onbase import parse_export, generate_syncback_bytes, write_syncback_to_outbox  # noqa: E402

# Path to OUTBOX directory (relative to repo root)
_OUTBOX_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "outbox"
)

_STATUS_EMOJI = {
    STATUS_SCHEDULED:      "📅 SCHEDULED",
    STATUS_CHECKED_IN:     "✅ CHECKED_IN",
    STATUS_IN_PROCESS:     "🔄 IN_PROCESS",
    STATUS_COMPLETED:      "🏁 COMPLETED",
    STATUS_NO_SHOW_PENDING:"⚠️ NO_SHOW_PENDING",
    STATUS_NO_SHOW:        "❌ NO_SHOW",
}


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

    df = pd.DataFrame(appointments)
    display_df = df[[
        "appointment_key", "sets_number", "testing_datetime",
        "final_status", "checkin_time", "in_process_time",
        "completed_time", "no_show_time", "last_updated_by", "notes",
    ]].copy()
    display_df["final_status"] = display_df["final_status"].apply(
        lambda s: _STATUS_EMOJI.get(s, s)
    )
    display_df.columns = [
        "Appt Key", "SETS #", "Testing Date/Time",
        "Status", "Check-In", "In-Process",
        "Completed", "No-Show", "Updated By", "Notes",
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── 3. No-Show Flagging ──────────────────────────────────────────────────
    st.header("3. Flag No-Shows")
    st.markdown(
        "Mark **SCHEDULED** patients who have not arrived as candidate No-Shows. "
        "These are not finalised until you click **Finalize** below."
    )

    scheduled = [a for a in appointments if a["final_status"] == STATUS_SCHEDULED]
    pending = [a for a in appointments if a["final_status"] == STATUS_NO_SHOW_PENDING]

    if scheduled or pending:
        col_headers = st.columns([3, 2, 2])
        col_headers[0].markdown("**SETS # / Appt Key**")
        col_headers[1].markdown("**Testing Date/Time**")
        col_headers[2].markdown("**Action**")

        for appt in scheduled:
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.write(f"SETS: {appt['sets_number']}  \n`{appt['appointment_key']}`")
            c2.write(appt["testing_datetime"])
            if c3.button("Flag No-Show", key=f"flag_{appt['sets_number']}"):
                flag_no_show(st, appt["sets_number"])
                st.rerun()

        for appt in pending:
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.write(f"⚠️ SETS: {appt['sets_number']}  \n`{appt['appointment_key']}`")
            c2.write(appt["testing_datetime"])
            if c3.button("↩ Undo Flag", key=f"unflag_{appt['sets_number']}"):
                unflag_no_show(st, appt["sets_number"])
                st.rerun()
    else:
        st.info("No SCHEDULED or flagged patients to display.")

    # ── 4. Finalize No-Shows ─────────────────────────────────────────────────
    st.header("4. Finalize No-Shows")
    pending_count = sum(1 for a in appointments if a["final_status"] == STATUS_NO_SHOW_PENDING)
    if pending_count:
        st.warning(
            f"There are **{pending_count}** flagged No-Show candidates. "
            "Finalizing will permanently mark them as NO_SHOW and set `no_show_time`."
        )
        if st.button("⚠️ Finalize No-Shows", type="primary"):
            count = finalize_no_shows(st)
            st.success(f"✅ {count} appointment(s) finalized as NO_SHOW.")
            st.rerun()
    else:
        st.info("No pending No-Show flags to finalize.")

    # ── 5. OnBase Sync-Back ──────────────────────────────────────────────────
    st.header("5. Generate OnBase Sync-Back File")
    st.markdown(
        "Generates **`GT_RESULTS_YYYYMMDD_HHMMSS.csv`** with all 11 OnBase columns "
        "for re-import (Method A: CSV Drop to OUTBOX).  \n"
        "Matching: `appointment_key` (primary) or `sets_number` + `testing_datetime` (fallback)."
    )

    col_dl, col_out = st.columns(2)

    with col_dl:
        csv_bytes = generate_syncback_bytes(appointments)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="⬇️ Download Sync-Back CSV",
            data=csv_bytes,
            file_name=f"GT_RESULTS_{ts}.csv",
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
