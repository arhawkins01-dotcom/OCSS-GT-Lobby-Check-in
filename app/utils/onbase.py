"""
OnBase CSV utilities for the OCSS GT Lobby Check-In application.

parse_export(file_obj)
    Reads an OnBase appointment export CSV and returns a list of dicts.

generate_syncback(appointments, outbox_dir)
    Writes a dated sync-back CSV to *outbox_dir* and returns the file path.
    The file can also be returned as bytes for an in-browser download.
"""

import io
import os
from datetime import datetime, timezone

import pandas as pd


# ---------------------------------------------------------------------------
# Column mapping: OnBase export header → internal key
# Accepts both exact-match and case-insensitive snake_case variants.
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: dict[str, str] = {
    "sets_number": "sets_number",
    "setsnumber": "sets_number",
    "sets number": "sets_number",
    "id": "sets_number",
    "last_name": "last_name",
    "lastname": "last_name",
    "last name": "last_name",
    "surname": "last_name",
    "first_name": "first_name",
    "firstname": "first_name",
    "first name": "first_name",
    "given name": "first_name",
    "dob": "dob",
    "date_of_birth": "dob",
    "date of birth": "dob",
    "birthdate": "dob",
    "appt_datetime": "appt_datetime",
    "appt datetime": "appt_datetime",
    "appointment_datetime": "appt_datetime",
    "appointment datetime": "appt_datetime",
    "appointment date": "appt_datetime",
    "appt_type": "appt_type",
    "appt type": "appt_type",
    "appointment_type": "appt_type",
    "appointment type": "appt_type",
    "type": "appt_type",
    "status": "status",
}

_REQUIRED_INTERNAL = {"sets_number", "last_name"}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns to internal keys using _COLUMN_ALIASES."""
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COLUMN_ALIASES:
            rename_map[col] = _COLUMN_ALIASES[key]
    return df.rename(columns=rename_map)


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
        One dict per appointment row, using internal field names.

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
            "Expected headers (case-insensitive): sets_number, last_name."
        )

    # Ensure optional columns exist with empty defaults
    for col in ("first_name", "dob", "appt_datetime", "appt_type", "status"):
        if col not in df.columns:
            df[col] = ""

    # Default empty status to Scheduled
    df["status"] = df["status"].apply(
        lambda s: s.strip() if s.strip() else "Scheduled"
    )

    return df[
        ["sets_number", "last_name", "first_name", "dob", "appt_datetime", "appt_type", "status"]
    ].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Sync-back generation
# ---------------------------------------------------------------------------

_SYNCBACK_COLUMNS = [
    "sets_number",
    "last_name",
    "first_name",
    "dob",
    "appt_datetime",
    "appt_type",
    "status",
    "checkin_time",
    "start_time",
    "complete_time",
]

# Map internal No-Show-Pending back to No-Show in the export
_STATUS_EXPORT_MAP = {
    "No-Show-Pending": "No-Show",
}


def _export_status(status: str) -> str:
    return _STATUS_EXPORT_MAP.get(status, status)


def generate_syncback_bytes(appointments: list[dict]) -> bytes:
    """
    Build the sync-back CSV content and return it as UTF-8 bytes.

    Parameters
    ----------
    appointments : list[dict]
        Current appointment records from session state.

    Returns
    -------
    bytes
        UTF-8 encoded CSV content ready for download or file write.
    """
    rows = []
    for appt in appointments:
        row = {col: appt.get(col, "") for col in _SYNCBACK_COLUMNS}
        row["status"] = _export_status(row["status"])
        rows.append(row)

    df = pd.DataFrame(rows, columns=_SYNCBACK_COLUMNS)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def write_syncback_to_outbox(appointments: list[dict], outbox_dir: str) -> str:
    """
    Write the sync-back CSV to *outbox_dir* with a timestamp in the filename.

    Returns
    -------
    str
        Full path to the written file.
    """
    os.makedirs(outbox_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"onbase_syncback_{timestamp}.csv"
    filepath = os.path.join(outbox_dir, filename)

    content = generate_syncback_bytes(appointments)
    with open(filepath, "wb") as fh:
        fh.write(content)

    return filepath
