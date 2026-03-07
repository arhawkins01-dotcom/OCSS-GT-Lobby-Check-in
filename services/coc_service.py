"""Chain of custody form services."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine


VALID_COC_STATUSES = {"DRAFT", "COMPLETED", "PRINTED"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_appointment_for_coc(engine: Engine, appointment_key: str):
    q = text(
        """
        SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.p_number,
               a.first_name, a.last_name, a.part_type, a.assigned_to,
               a.location, a.test_type,
               v.current_status, v.checkin_time
        FROM gt_appointments a
        JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
        WHERE a.appointment_key = :key
        """
    )
    with engine.begin() as conn:
        return conn.execute(q, {"key": appointment_key}).mappings().one_or_none()


def create_coc_form(
    engine: Engine,
    appointment_key: str,
    collector_name: str,
    collector_id: str | None = None,
    notes: str | None = None,
    generated_by: str = "STAFF",
) -> dict:
    """Create a chain-of-custody form row from appointment metadata."""
    appt = _get_appointment_for_coc(engine, appointment_key)
    if not appt:
        return {"error": "Appointment not found", "success": False}

    coc_id = str(uuid.uuid4())
    now = _now()
    participant_name = f"{appt.get('first_name', '')} {appt.get('last_name', '')}".strip()

    insert_q = text(
        """
        INSERT INTO coc_forms (
            coc_id, appointment_key, sets_case_number, p_number,
            participant_name, participant_role, appointment_datetime, checkin_time,
            location, test_type, collector_name, collector_id,
            staff_user, generated_by, generated_at,
            created_at, updated_at, status, notes
        ) VALUES (
            :coc_id, :appointment_key, :sets_case_number, :p_number,
            :participant_name, :participant_role, :appointment_datetime, :checkin_time,
            :location, :test_type, :collector_name, :collector_id,
            :staff_user, :generated_by, :generated_at,
            :created_at, :updated_at, :status, :notes
        )
        """
    )

    with engine.begin() as conn:
        conn.execute(
            insert_q,
            {
                "coc_id": coc_id,
                "appointment_key": appointment_key,
                "sets_case_number": appt.get("sets_number"),
                "p_number": appt.get("p_number"),
                "participant_name": participant_name,
                "participant_role": appt.get("part_type"),
                "appointment_datetime": appt.get("testing_datetime"),
                "checkin_time": appt.get("checkin_time"),
                "location": appt.get("location") or "OCSS Lobby",
                "test_type": appt.get("test_type") or "Genetic Testing",
                "collector_name": collector_name,
                "collector_id": collector_id,
                "staff_user": collector_name,
                "generated_by": generated_by,
                "generated_at": now,
                "created_at": now,
                "updated_at": now,
                "status": "DRAFT",
                "notes": notes,
            },
        )

    return {
        "success": True,
        "coc_id": coc_id,
        "appointment_key": appointment_key,
        "participant_name": participant_name,
        "sets_number": appt.get("sets_number"),
        "part_type": appt.get("part_type"),
        "testing_datetime": appt.get("testing_datetime"),
        "collector_name": collector_name,
        "created_at": now,
    }


def get_coc_form(engine: Engine, coc_id: str) -> dict | None:
    q = text("SELECT * FROM coc_forms WHERE coc_id = :coc_id")
    with engine.begin() as conn:
        result = conn.execute(q, {"coc_id": coc_id}).mappings().one_or_none()
    return dict(result) if result else None


def get_latest_coc_for_appointment(engine: Engine, appointment_key: str) -> dict | None:
    q = text(
        """
        SELECT *
        FROM coc_forms
        WHERE appointment_key = :appointment_key
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        result = conn.execute(q, {"appointment_key": appointment_key}).mappings().one_or_none()
    return dict(result) if result else None


def ensure_coc_for_checkin(engine: Engine, appointment_key: str, generated_by: str = "SYSTEM") -> dict:
    """Idempotently ensure at least one COC exists after check-in."""
    existing = get_latest_coc_for_appointment(engine, appointment_key)
    if existing:
        return {"success": True, "coc_id": existing.get("coc_id"), "created": False}

    created = create_coc_form(
        engine=engine,
        appointment_key=appointment_key,
        collector_name=generated_by,
        collector_id=None,
        notes="Auto-generated after successful check-in.",
        generated_by=generated_by,
    )
    return {"success": bool(created.get("success")), "coc_id": created.get("coc_id"), "created": True}


def update_coc_form_status(engine: Engine, coc_id: str, status: str) -> bool:
    new_status = str(status).strip().upper()
    if new_status not in VALID_COC_STATUSES:
        raise ValueError(f"Invalid COC status: {status}")

    q = text(
        """
        UPDATE coc_forms
        SET status = :status, updated_at = :updated_at
        WHERE coc_id = :coc_id
        """
    )
    with engine.begin() as conn:
        conn.execute(q, {"coc_id": coc_id, "status": new_status, "updated_at": _now()})
    return True
