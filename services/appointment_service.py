"""
appointment_service.py
----------------------
CRUD operations for the appointments table.
"""

import logging
from datetime import date
from typing import Optional

from services.database_service import execute_many, execute_query, execute_write

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def get_appointments_for_date(appt_date: date) -> list[dict]:
    """Return all appointments for the given date."""
    sql = """
        SELECT *
        FROM   appointments
        WHERE  appointment_date = ?
        ORDER  BY appointment_time
    """
    return execute_query(sql, (appt_date.isoformat(),))


def get_appointment_by_id(appointment_id: str) -> Optional[dict]:
    """Return a single appointment by its primary key, or None."""
    sql = "SELECT * FROM appointments WHERE appointment_id = ?"
    rows = execute_query(sql, (appointment_id,))
    return rows[0] if rows else None


def find_appointments(
    gt_id: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    appt_date: Optional[date] = None,
) -> list[dict]:
    """
    Flexible appointment lookup.  Provide gt_id OR (first_name AND last_name).
    Optionally filter by appointment_date.
    """
    conditions: list[str] = []
    params: list = []

    if gt_id:
        conditions.append("student_gt_id = ?")
        params.append(gt_id.strip().lower())
    elif first_name and last_name:
        conditions.append("LOWER(student_first_name) = ?")
        conditions.append("LOWER(student_last_name) = ?")
        params.append(first_name.strip().lower())
        params.append(last_name.strip().lower())

    if appt_date:
        conditions.append("appointment_date = ?")
        params.append(appt_date.isoformat())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM appointments {where} ORDER BY appointment_date, appointment_time"
    return execute_query(sql, tuple(params))


# ---------------------------------------------------------------------------
# Upsert (bulk load from OnBase export)
# ---------------------------------------------------------------------------

def bulk_upsert_appointments(records: list[dict]) -> int:
    """
    Insert or replace appointment records.
    Returns the number of rows affected.
    """
    sql = """
        INSERT OR REPLACE INTO appointments
            (appointment_id, student_gt_id, student_first_name, student_last_name,
             student_email, appointment_date, appointment_time, appointment_type,
             counselor, status, notes, updated_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """
    params_list = [
        (
            r["appointment_id"],
            r["student_gt_id"],
            r["student_first_name"],
            r["student_last_name"],
            r.get("student_email", ""),
            r["appointment_date"],
            r["appointment_time"],
            r["appointment_type"],
            r.get("counselor", ""),
            r.get("status", "Scheduled"),
            r.get("notes", ""),
        )
        for r in records
    ]
    affected = execute_many(sql, params_list)
    logger.info("Upserted %d appointment records", affected)
    return affected


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

def update_appointment_status(appointment_id: str, status: str) -> None:
    """Update the status field for a single appointment."""
    sql = """
        UPDATE appointments
        SET    status = ?, updated_at = datetime('now')
        WHERE  appointment_id = ?
    """
    execute_write(sql, (status, appointment_id))
    logger.debug("Appointment %s status → %s", appointment_id, status)
