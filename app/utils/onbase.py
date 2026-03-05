"""
OnBase CSV utilities for the OCSS GT Lobby Check-In application.

parse_export(file_obj)
    Reads an OnBase appointment export CSV and returns a list of dicts.

generate_syncback_bytes(appointments)
    Returns the sync-back CSV as UTF-8 bytes for download.

write_syncback_to_outbox(appointments, outbox_dir)
    Writes a GT_RESULTS_YYYYMMDD_HHMMSS.csv to *outbox_dir* (Method A).

Sync-back spec
--------------
File name : GT_RESULTS_YYYYMMDD_HHMMSS.csv
Columns   : appointment_key, sets_number, testing_datetime, final_status,
            checkin_time, in_process_time, completed_time, no_show_time,
            last_updated_by, last_updated_time, notes
Matching  : appointment_key (primary); sets_number + testing_datetime (fallback)
"""

import io
import os
from datetime import datetime

import pandas as pd


# ---------------------------------------------------------------------------
# Column mapping: OnBase export header → internal key
# Accepts exact-match and common case-insensitive / spaced variants.
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: dict[str, str] = {
    # appointment_key
    "appointment_key":          "appointment_key",
    "appt_key":                 "appointment_key",
    "apptkey":                  "appointment_key",
    # sets_number
    "sets_number":              "sets_number",
    "setsnumber":               "sets_number",
    "sets number":              "sets_number",
    "id":                       "sets_number",
    # testing_datetime
    "testing_datetime":         "testing_datetime",
    "testing datetime":         "testing_datetime",
    "appt_datetime":            "testing_datetime",
    "appt datetime":            "testing_datetime",
    "appointment_datetime":     "testing_datetime",
    "appointment datetime":     "testing_datetime",
    "appointment date":         "testing_datetime",
    # final_status
    "final_status":             "final_status",
    "final status":             "final_status",
    "status":                   "final_status",
    # checkin_time
    "checkin_time":             "checkin_time",
    "checkin time":             "checkin_time",
    "check_in_time":            "checkin_time",
    "check in time":            "checkin_time",
    # in_process_time
    "in_process_time":          "in_process_time",
    "in process time":          "in_process_time",
    "start_time":               "in_process_time",
    "start time":               "in_process_time",
    # completed_time
    "completed_time":           "completed_time",
    "completed time":           "completed_time",
    "complete_time":            "completed_time",
    "complete time":            "completed_time",
    # no_show_time
    "no_show_time":             "no_show_time",
    "no show time":             "no_show_time",
    "noshow_time":              "no_show_time",
    # last_updated_by
    "last_updated_by":          "last_updated_by",
    "last updated by":          "last_updated_by",
    "updated_by":               "last_updated_by",
    # last_updated_time
    "last_updated_time":        "last_updated_time",
    "last updated time":        "last_updated_time",
    "updated_time":             "last_updated_time",
    # notes
    "notes":                    "notes",
    "note":                     "notes",
    "comments":                 "notes",
}

_REQUIRED_INTERNAL = {"sets_number"}

# Ordered columns for both parsing output and sync-back
ONBASE_COLUMNS = [
    "appointment_key",
    "sets_number",
    "testing_datetime",
    "final_status",
    "checkin_time",
    "in_process_time",
    "completed_time",
    "no_show_time",
    "last_updated_by",
    "last_updated_time",
    "notes",
]

# Internal-only status that must be mapped before writing back to OnBase
_STATUS_EXPORT_MAP = {
    "NO_SHOW_PENDING": "NO_SHOW",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns to internal keys using _COLUMN_ALIASES."""
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COLUMN_ALIASES:
            rename_map[col] = _COLUMN_ALIASES[key]
    return df.rename(columns=rename_map)


def _export_status(status: str) -> str:
    return _STATUS_EXPORT_MAP.get(status, status)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def parse_export(file_obj) -> list[dict]:
    """
    Parse an OnBase appointment export CSV.

    Parameters
    ----------
    file_obj : file-like object or path string
        The uploaded CSV file.

    Returns
    -------
    list[dict]
        One dict per appointment row using internal field names.

    Raises
    ------
    ValueError
        If required columns are missing after alias resolution.
    """
    df = pd.read_csv(file_obj, dtype=str)
    df = _normalise_columns(df)
    df = df.fillna("")

    missing = _REQUIRED_INTERNAL - set(df.columns)
    if missing:
        raise ValueError(
            f"Required column(s) not found in CSV: {', '.join(sorted(missing))}. "
            "Expected header: sets_number."
        )

    # Ensure all expected columns exist with empty defaults
    for col in ONBASE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Auto-generate appointment_key when absent: {sets_number}_{YYYYMMDDHHmm}
    def _make_key(row: "pd.Series") -> str:
        if row["appointment_key"].strip():
            return row["appointment_key"].strip()
        try:
            # strptime accepts both zero-padded ('03/05/2026 09:00') and
            # non-zero-padded ('3/5/2026 9:00') values, matching OnBase M/D/YYYY H:MM.
            dt = datetime.strptime(row["testing_datetime"].strip(), "%m/%d/%Y %H:%M")
            return f"{row['sets_number'].strip()}_{dt.strftime('%Y%m%d%H%M')}"
        except ValueError:
            return f"{row['sets_number'].strip()}_{row['testing_datetime'].strip()}"

    df["appointment_key"] = df.apply(_make_key, axis=1)

    # Default empty final_status to SCHEDULED
    df["final_status"] = df["final_status"].apply(
        lambda s: s.strip() if s.strip() else "SCHEDULED"
    )

    return df[ONBASE_COLUMNS].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Sync-back generation (Method A — CSV Drop to OUTBOX)
# ---------------------------------------------------------------------------

def generate_syncback_bytes(appointments: list[dict]) -> bytes:
    """
    Build the GT_RESULTS sync-back CSV and return it as UTF-8 bytes.

    Columns follow the OnBase sync-back spec exactly.
    Internal status NO_SHOW_PENDING is mapped to NO_SHOW before export.
    """
    rows = []
    for appt in appointments:
        row = {col: appt.get(col, "") for col in ONBASE_COLUMNS}
        row["final_status"] = _export_status(row["final_status"])
        rows.append(row)

    df = pd.DataFrame(rows, columns=ONBASE_COLUMNS)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def write_syncback_to_outbox(appointments: list[dict], outbox_dir: str) -> str:
    """
    Write the sync-back CSV to *outbox_dir*.

    File is named GT_RESULTS_YYYYMMDD_HHMMSS.csv per the OnBase sync spec.

    Returns
    -------
    str
        Full path to the written file.
    """
    os.makedirs(outbox_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"GT_RESULTS_{timestamp}.csv"
    filepath = os.path.join(outbox_dir, filename)

    content = generate_syncback_bytes(appointments)
    with open(filepath, "wb") as fh:
        fh.write(content)

    return filepath
