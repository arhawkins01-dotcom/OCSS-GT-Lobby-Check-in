"""
checkin_service.py
------------------
Manages check-in records: creation, status transitions, and queue queries.
"""

import logging
import uuid
from datetime import date, datetime
from typing import Optional

from services.database_service import execute_query, execute_write

logger = logging.getLogger(__name__)

# Valid status transitions
_VALID_STATUSES = {"Waiting", "In-Progress", "Completed", "NoShow"}


# ---------------------------------------------------------------------------
# Queue retrieval
# ---------------------------------------------------------------------------

def get_active_queue(queue_date: Optional[date] = None) -> list[dict]:
    """
    Return all check-ins with status Waiting or In-Progress for the given
    date (defaults to today).  Joins with appointments for display fields.
    """
    if queue_date is None:
        queue_date = date.today()

    sql = """
        SELECT
            ci.checkin_id,
            ci.appointment_id,
            ci.student_gt_id,
            ci.checkin_timestamp,
            ci.checkin_status,
            ci.notes        AS checkin_notes,
            a.student_first_name,
            a.student_last_name,
            a.appointment_time,
            a.appointment_type,
            a.counselor
        FROM   check_ins ci
        JOIN   appointments a ON a.appointment_id = ci.appointment_id
        WHERE  DATE(ci.checkin_timestamp) = ?
          AND  ci.checkin_status IN ('Waiting', 'In-Progress')
        ORDER  BY ci.checkin_timestamp
    """
    return execute_query(sql, (queue_date.isoformat(),))


def get_all_checkins_for_date(queue_date: date) -> list[dict]:
    """Return all check-in records (any status) for the specified date."""
    sql = """
        SELECT
            ci.*,
            a.student_first_name,
            a.student_last_name,
            a.appointment_time,
            a.appointment_type,
            a.counselor
        FROM   check_ins ci
        JOIN   appointments a ON a.appointment_id = ci.appointment_id
        WHERE  DATE(ci.checkin_timestamp) = ?
        ORDER  BY ci.checkin_timestamp
    """
    return execute_query(sql, (queue_date.isoformat(),))


# ---------------------------------------------------------------------------
# Check-in creation
# ---------------------------------------------------------------------------

def create_checkin(appointment_id: str, student_gt_id: str, notes: str = "") -> str:
    """
    Create a new check-in record for the given appointment.
    Returns the new checkin_id.
    Raises ValueError if the appointment already has an active check-in today.
    """
    # Guard against duplicate check-ins on the same day
    existing = execute_query(
        """
        SELECT checkin_id FROM check_ins
        WHERE  appointment_id = ?
          AND  DATE(checkin_timestamp) = DATE('now')
          AND  checkin_status != 'NoShow'
        """,
        (appointment_id,),
    )
    if existing:
        raise ValueError(
            f"Appointment {appointment_id} already has an active check-in today."
        )

    checkin_id = f"CHK-{uuid.uuid4().hex[:8].upper()}"
    sql = """
        INSERT INTO check_ins
            (checkin_id, appointment_id, student_gt_id, checkin_status, notes)
        VALUES (?, ?, ?, 'Waiting', ?)
    """
    execute_write(sql, (checkin_id, appointment_id, student_gt_id, notes))
    logger.info("Check-in created: %s for appointment %s", checkin_id, appointment_id)
    return checkin_id


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

def update_checkin_status(checkin_id: str, new_status: str) -> None:
    """Update the status of a check-in record."""
    if new_status not in _VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {_VALID_STATUSES}.")

    extra_sql = ""
    if new_status == "Completed":
        extra_sql = ", checkout_timestamp = datetime('now')"

    sql = f"""
        UPDATE check_ins
        SET    checkin_status = ?, updated_at = datetime('now'){extra_sql}
        WHERE  checkin_id = ?
    """
    execute_write(sql, (new_status, checkin_id))
    logger.debug("Check-in %s status → %s", checkin_id, new_status)


def finalize_no_shows(appt_date: date, finalized_by: str) -> int:
    """
    Mark all appointments on appt_date that lack a check-in as NoShow.
    Returns the number of records created.
    """
    # Find appointments with no check-in today
    sql_find = """
        SELECT a.appointment_id, a.student_gt_id
        FROM   appointments a
        LEFT JOIN check_ins ci
               ON ci.appointment_id = a.appointment_id
              AND DATE(ci.checkin_timestamp) = ?
        WHERE  a.appointment_date = ?
          AND  ci.checkin_id IS NULL
    """
    unmatched = execute_query(sql_find, (appt_date.isoformat(), appt_date.isoformat()))

    count = 0
    for row in unmatched:
        checkin_id = f"NSH-{uuid.uuid4().hex[:8].upper()}"
        sql_insert = """
            INSERT INTO check_ins
                (checkin_id, appointment_id, student_gt_id,
                 checkin_timestamp, checkin_status, no_show_flag,
                 no_show_finalized_by, no_show_finalized_at)
            VALUES (?, ?, ?, datetime('now'), 'NoShow', 1, ?, datetime('now'))
        """
        execute_write(
            sql_insert,
            (checkin_id, row["appointment_id"], row["student_gt_id"], finalized_by),
        )
        count += 1

    logger.info(
        "Finalized %d no-shows for %s by %s", count, appt_date.isoformat(), finalized_by
    )
    return count
