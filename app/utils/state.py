"""
Shared session-state helpers for the OCSS GT Lobby Check-In application.

The in-memory store lives in st.session_state under the key "appointments",
which is a list of dicts mirroring the OnBase export/sync-back schema.

Record schema (matches OnBase CSV columns)
------------------------------------------
appointment_key    : str  – "{sets_number}_{YYYYMMDDHHmm}"
sets_number        : str
testing_datetime   : str  – "M/D/YYYY H:MM"
final_status       : str  – SCHEDULED | CHECKED_IN | IN_PROCESS | COMPLETED | NO_SHOW
                            (NO_SHOW_PENDING is internal-only, exported as NO_SHOW)
checkin_time       : str | ""  – "M/D/YYYY H:MM"
in_process_time    : str | ""  – "M/D/YYYY H:MM"
completed_time     : str | ""  – "M/D/YYYY H:MM"
no_show_time       : str | ""  – "M/D/YYYY H:MM"
last_updated_by    : str | ""
last_updated_time  : str | ""  – "M/D/YYYY H:MM"
notes              : str | ""
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------
STATUS_SCHEDULED = "SCHEDULED"
STATUS_CHECKED_IN = "CHECKED_IN"
STATUS_IN_PROCESS = "IN_PROCESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_NO_SHOW = "NO_SHOW"
STATUS_NO_SHOW_PENDING = "NO_SHOW_PENDING"  # internal staging state

KIOSK_ACTOR = "KIOSK"
STAFF_ACTOR = "GT Clerk"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_onbase() -> str:
    """Return current local time in OnBase M/D/YYYY H:MM format (no leading zeros).

    Matches the OnBase datetime convention seen in the export spec, e.g. '3/5/2026 8:52'.
    Minutes are always two digits; month, day, and hour have no leading zeros.
    """
    now = datetime.now()
    return f"{now.month}/{now.day}/{now.year} {now.hour}:{now.minute:02d}"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_state(st) -> None:
    """Ensure all required session-state keys exist."""
    if "appointments" not in st.session_state:
        st.session_state["appointments"] = []
    if "export_loaded" not in st.session_state:
        st.session_state["export_loaded"] = False


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

def get_appointments(st) -> list[dict]:
    return st.session_state.get("appointments", [])


def find_appointment(st, sets_number: str) -> dict | None:
    """Return the appointment record for *sets_number*, or None."""
    sets_number = sets_number.strip()
    for appt in get_appointments(st):
        if str(appt["sets_number"]).strip() == sets_number:
            return appt
    return None


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------

def load_appointments(st, records: list[dict]) -> None:
    """Replace the appointment list with *records* (from OnBase import)."""
    normalised = []
    for r in records:
        normalised.append({
            "appointment_key":   str(r.get("appointment_key", "")).strip(),
            "sets_number":       str(r.get("sets_number", "")).strip(),
            "testing_datetime":  str(r.get("testing_datetime", "")).strip(),
            "final_status":      str(r.get("final_status", STATUS_SCHEDULED)).strip() or STATUS_SCHEDULED,
            "checkin_time":      str(r.get("checkin_time", "")).strip(),
            "in_process_time":   str(r.get("in_process_time", "")).strip(),
            "completed_time":    str(r.get("completed_time", "")).strip(),
            "no_show_time":      str(r.get("no_show_time", "")).strip(),
            "last_updated_by":   str(r.get("last_updated_by", "")).strip(),
            "last_updated_time": str(r.get("last_updated_time", "")).strip(),
            "notes":             str(r.get("notes", "")).strip(),
        })
    st.session_state["appointments"] = normalised
    st.session_state["export_loaded"] = True


def check_in(st, sets_number: str, last_name: str) -> tuple[bool, str]:
    """
    Attempt to check in a patient.

    Validates that the SETS Number exists in the loaded schedule.
    Last Name is not stored in the OnBase export, so it is appended to the
    appointment's notes field for audit purposes rather than validated.

    Returns (success, message).
    """
    sets_number = sets_number.strip()
    last_name = last_name.strip()

    if not sets_number or not last_name:
        return False, "Please enter both your SETS Number and Last Name."

    appt = find_appointment(st, sets_number)
    if appt is None:
        return False, "No appointment found for that SETS Number. Please see the front desk."

    status = appt["final_status"]

    if status == STATUS_CHECKED_IN:
        return False, "You have already checked in. Please take a seat."

    if status in (STATUS_IN_PROCESS, STATUS_COMPLETED):
        return False, f"Your appointment is already marked as {status.replace('_', ' ').title()}."

    if status == STATUS_NO_SHOW:
        return False, "Your appointment has been marked as a No-Show. Please see the front desk."

    if status == STATUS_NO_SHOW_PENDING:
        return False, "Your appointment has been flagged — please see the front desk."

    now = _now_onbase()
    appt["final_status"] = STATUS_CHECKED_IN
    appt["checkin_time"] = now
    appt["last_updated_by"] = KIOSK_ACTOR
    appt["last_updated_time"] = now
    # Append last name to notes for identity audit trail
    last_name_note = f"Checked in as: {last_name}"
    appt["notes"] = (appt["notes"] + "; " + last_name_note).lstrip("; ")

    return True, (
        f"Check-in successful! SETS {sets_number} — {appt['testing_datetime']}. "
        "Please take a seat and a staff member will call you shortly."
    )


def start_appointment(st, sets_number: str, updated_by: str = STAFF_ACTOR) -> None:
    """Move appointment from CHECKED_IN → IN_PROCESS."""
    appt = find_appointment(st, sets_number)
    if appt and appt["final_status"] == STATUS_CHECKED_IN:
        now = _now_onbase()
        appt["final_status"] = STATUS_IN_PROCESS
        appt["in_process_time"] = now
        appt["last_updated_by"] = updated_by
        appt["last_updated_time"] = now


def complete_appointment(st, sets_number: str, updated_by: str = STAFF_ACTOR) -> None:
    """Move appointment from IN_PROCESS → COMPLETED."""
    appt = find_appointment(st, sets_number)
    if appt and appt["final_status"] == STATUS_IN_PROCESS:
        now = _now_onbase()
        appt["final_status"] = STATUS_COMPLETED
        appt["completed_time"] = now
        appt["last_updated_by"] = updated_by
        appt["last_updated_time"] = now


def flag_no_show(st, sets_number: str, updated_by: str = STAFF_ACTOR) -> None:
    """Flag a SCHEDULED appointment as a candidate No-Show (pending admin finalisation)."""
    appt = find_appointment(st, sets_number)
    if appt and appt["final_status"] == STATUS_SCHEDULED:
        appt["final_status"] = STATUS_NO_SHOW_PENDING
        appt["last_updated_by"] = updated_by
        appt["last_updated_time"] = _now_onbase()


def unflag_no_show(st, sets_number: str, updated_by: str = STAFF_ACTOR) -> None:
    """Revert a NO_SHOW_PENDING flag back to SCHEDULED."""
    appt = find_appointment(st, sets_number)
    if appt and appt["final_status"] == STATUS_NO_SHOW_PENDING:
        appt["final_status"] = STATUS_SCHEDULED
        appt["last_updated_by"] = updated_by
        appt["last_updated_time"] = _now_onbase()


def finalize_no_shows(st, updated_by: str = STAFF_ACTOR) -> int:
    """Confirm all NO_SHOW_PENDING appointments as NO_SHOW. Returns count finalized."""
    count = 0
    for appt in get_appointments(st):
        if appt["final_status"] == STATUS_NO_SHOW_PENDING:
            now = _now_onbase()
            appt["final_status"] = STATUS_NO_SHOW
            appt["no_show_time"] = now
            appt["last_updated_by"] = updated_by
            appt["last_updated_time"] = now
            count += 1
    return count
