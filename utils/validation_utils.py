"""
validation_utils.py
-------------------
Input validation helpers: GT ID format, dates, names, etc.
"""

import re
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# GT ID
# ---------------------------------------------------------------------------

_GT_ID_PATTERN = re.compile(r"^gt\d{6,9}$", re.IGNORECASE)


def is_valid_gt_id(gt_id: str) -> bool:
    """Return True if gt_id matches the format gtNNNNNN (6–9 digits)."""
    return bool(_GT_ID_PATTERN.match(gt_id.strip()))


def normalise_gt_id(gt_id: str) -> str:
    """Return a lowercase, stripped GT ID."""
    return gt_id.strip().lower()


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

def is_valid_name(name: str) -> bool:
    """Return True if name is a non-empty string containing only letters, spaces, hyphens, and apostrophes."""
    return bool(name) and bool(re.match(r"^[A-Za-z\s\-']+$", name.strip()))


# ---------------------------------------------------------------------------
# Date / time
# ---------------------------------------------------------------------------

def is_valid_date_string(date_str: str, fmt: str = "%Y-%m-%d") -> bool:
    """Return True if date_str can be parsed with fmt."""
    try:
        datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> Optional[date]:
    """Parse a date string.  Returns None on failure."""
    try:
        return datetime.strptime(date_str, fmt).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Appointment record validation
# ---------------------------------------------------------------------------

_REQUIRED_APPT_FIELDS = [
    "appointment_id",
    "student_gt_id",
    "student_first_name",
    "student_last_name",
    "appointment_date",
    "appointment_time",
    "appointment_type",
]


def validate_appointment_record(record: dict) -> list[str]:
    """
    Validate a single appointment record dict.
    Returns a list of error messages (empty list = valid).
    """
    errors: list[str] = []

    for field in _REQUIRED_APPT_FIELDS:
        if not record.get(field):
            errors.append(f"Missing required field: '{field}'")

    gt_id = record.get("student_gt_id", "")
    if gt_id and not is_valid_gt_id(gt_id):
        errors.append(f"Invalid GT ID format: '{gt_id}' (expected gtNNNNNN)")

    appt_date = record.get("appointment_date", "")
    if appt_date and not is_valid_date_string(appt_date):
        errors.append(f"Invalid appointment_date format: '{appt_date}' (expected YYYY-MM-DD)")

    return errors


def validate_appointment_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Validate a list of appointment record dicts.
    Returns (valid_records, invalid_records).
    Each invalid record has an extra '_errors' key with a list of error messages.
    """
    valid: list[dict] = []
    invalid: list[dict] = []

    for record in records:
        errors = validate_appointment_record(record)
        if errors:
            record_copy = dict(record)
            record_copy["_errors"] = errors
            invalid.append(record_copy)
        else:
            valid.append(record)

    return valid, invalid
