"""
Shared session-state helpers for the OCSS GT Lobby Check-In application.

The in-memory store lives in st.session_state under the key "appointments",
which is a list of dicts, each representing one appointment record.

Record schema
-------------
sets_number : str
last_name   : str  (uppercase, trimmed)
first_name  : str
dob         : str
appt_datetime : str
appt_type   : str
status      : str  – one of: Scheduled | Checked-In | In-Progress | Completed | No-Show
checkin_time  : str | None
start_time    : str | None
complete_time : str | None
"""

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_state(st) -> None:
    """Ensure all required session-state keys exist."""
    if "appointments" not in st.session_state:
        st.session_state["appointments"] = []
    if "export_loaded" not in st.session_state:
        st.session_state["export_loaded"] = False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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
            "sets_number": str(r.get("sets_number", "")).strip(),
            "last_name": str(r.get("last_name", "")).strip().upper(),
            "first_name": str(r.get("first_name", "")).strip(),
            "dob": str(r.get("dob", "")).strip(),
            "appt_datetime": str(r.get("appt_datetime", "")).strip(),
            "appt_type": str(r.get("appt_type", "")).strip(),
            "status": str(r.get("status", "Scheduled")).strip(),
            "checkin_time": None,
            "start_time": None,
            "complete_time": None,
        })
    st.session_state["appointments"] = normalised
    st.session_state["export_loaded"] = True


def check_in(st, sets_number: str, last_name: str) -> tuple[bool, str]:
    """
    Attempt to check in a patient.

    Returns (success, message).
    """
    sets_number = sets_number.strip()
    last_name = last_name.strip().upper()

    if not sets_number or not last_name:
        return False, "Please enter both your SETS Number and Last Name."

    appt = find_appointment(st, sets_number)
    if appt is None:
        return False, "No appointment found for that SETS Number. Please see the front desk."

    if appt["last_name"] != last_name:
        return False, "Last name does not match our records. Please see the front desk."

    if appt["status"] == "Checked-In":
        return False, "You have already checked in. Please take a seat."

    if appt["status"] in ("In-Progress", "Completed"):
        return False, f"Your appointment is already marked as {appt['status']}."

    if appt["status"] == "No-Show":
        return False, "Your appointment has been marked as a No-Show. Please see the front desk."

    appt["status"] = "Checked-In"
    appt["checkin_time"] = _now()
    return True, (
        f"Check-in successful! Welcome, {appt['first_name']} {appt['last_name'].title()}. "
        "Please take a seat and a staff member will call you shortly."
    )


def start_appointment(st, sets_number: str) -> None:
    """Move appointment from Checked-In → In-Progress."""
    appt = find_appointment(st, sets_number)
    if appt and appt["status"] == "Checked-In":
        appt["status"] = "In-Progress"
        appt["start_time"] = _now()


def complete_appointment(st, sets_number: str) -> None:
    """Move appointment from In-Progress → Completed."""
    appt = find_appointment(st, sets_number)
    if appt and appt["status"] == "In-Progress":
        appt["status"] = "Completed"
        appt["complete_time"] = _now()


def flag_no_show(st, sets_number: str) -> None:
    """Flag a Scheduled appointment as a candidate No-Show (pending admin finalisation)."""
    appt = find_appointment(st, sets_number)
    if appt and appt["status"] == "Scheduled":
        appt["status"] = "No-Show-Pending"


def unflag_no_show(st, sets_number: str) -> None:
    """Revert a No-Show-Pending flag back to Scheduled."""
    appt = find_appointment(st, sets_number)
    if appt and appt["status"] == "No-Show-Pending":
        appt["status"] = "Scheduled"


def finalize_no_shows(st) -> int:
    """Confirm all No-Show-Pending appointments as No-Show. Returns count finalized."""
    count = 0
    for appt in get_appointments(st):
        if appt["status"] == "No-Show-Pending":
            appt["status"] = "No-Show"
            count += 1
    return count
