"""
file_utils.py
-------------
CSV import/export helpers and OnBase file parsing.
"""

import csv
import io
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OnBase export parsing
# ---------------------------------------------------------------------------

_ONBASE_REQUIRED_COLUMNS = {
    "appointment_id",
    "student_gt_id",
    "student_first_name",
    "student_last_name",
    "appointment_date",
    "appointment_time",
    "appointment_type",
}


def parse_onbase_export(file_content: bytes | str) -> tuple[list[dict], list[str]]:
    """
    Parse an OnBase appointment export CSV.

    Args:
        file_content: Raw bytes or string content of the uploaded CSV.

    Returns:
        (records, errors) where records is a list of dicts and errors is a
        list of human-readable error messages encountered during parsing.
    """
    errors: list[str] = []

    try:
        if isinstance(file_content, bytes):
            text = file_content.decode("utf-8-sig")
        else:
            text = file_content

        df = pd.read_csv(io.StringIO(text), dtype=str)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    except Exception as exc:
        return [], [f"Failed to read CSV: {exc}"]

    # Check required columns
    missing = _ONBASE_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
        return [], errors

    # Strip whitespace from all string cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # Fill NaN with empty string
    df = df.fillna("")

    records = df.to_dict(orient="records")
    logger.info("Parsed %d records from OnBase export", len(records))
    return records, errors


# ---------------------------------------------------------------------------
# Generic CSV export
# ---------------------------------------------------------------------------

def records_to_csv_bytes(records: list[dict], columns: Optional[list[str]] = None) -> bytes:
    """
    Convert a list of dicts to a UTF-8 CSV byte string suitable for
    Streamlit download_button.
    """
    if not records:
        return b""

    if columns is None:
        columns = list(records[0].keys())

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Sync file reading (for re-import / verification)
# ---------------------------------------------------------------------------

def read_sync_file(file_path: Path) -> list[dict]:
    """Read a previously generated OnBase sync CSV and return a list of dicts."""
    with open(file_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


# ---------------------------------------------------------------------------
# Export: check-ins for a date range
# ---------------------------------------------------------------------------

def build_export_dataframe(checkin_records: list[dict]) -> pd.DataFrame:
    """
    Convert check-in records (from checkin_service) into a formatted DataFrame
    suitable for CSV / Excel export.
    """
    if not checkin_records:
        return pd.DataFrame()

    df = pd.DataFrame(checkin_records)

    # Friendly column renaming
    rename_map = {
        "checkin_id": "Check-In ID",
        "appointment_id": "Appointment ID",
        "student_gt_id": "GT ID",
        "student_first_name": "First Name",
        "student_last_name": "Last Name",
        "appointment_time": "Appt Time",
        "appointment_type": "Appt Type",
        "counselor": "Counselor",
        "checkin_timestamp": "Check-In Time",
        "checkout_timestamp": "Check-Out Time",
        "checkin_status": "Status",
        "no_show_flag": "No-Show",
        "notes": "Notes",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df
