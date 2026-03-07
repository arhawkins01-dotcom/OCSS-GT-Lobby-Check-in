from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine


VALID_ARRIVAL_STATUSES = {
    "UNKNOWN",
    "PRESENT",
    "ABSENT",
    "CHECKED_IN_SEPARATELY",
    "NOT_REQUIRED",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_related_parties(engine: Engine, appointment_key: str) -> list[dict]:
    """
    Return related parties anchored by same SETS number and appointment day.

    Secondary anchor uses related_cases when available.
    """
    anchor_q = text(
        """
        SELECT appointment_key, sets_number, related_cases, testing_datetime
        FROM gt_appointments
        WHERE appointment_key = :appointment_key
        """
    )
    with engine.begin() as conn:
        anchor = conn.execute(anchor_q, {"appointment_key": appointment_key}).mappings().one_or_none()
        if not anchor:
            return []

        day = str(anchor["testing_datetime"])[:10]
        sets_number = anchor.get("sets_number")
        related_cases = anchor.get("related_cases")

        parties_q = text(
            """
            SELECT a.appointment_key, a.first_name, a.last_name, a.part_type,
                   a.sets_number, a.p_number, a.related_cases, a.testing_datetime,
                   v.current_status,
                   s.arrival_status, s.identity_verified_flag, s.coc_included_flag,
                   s.updated_by, s.updated_time
            FROM gt_appointments a
            JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
            LEFT JOIN gt_related_party_status s
              ON s.appointment_key = :anchor_key
             AND s.related_appointment_key = a.appointment_key
            WHERE substr(a.testing_datetime,1,10) = :day
              AND (
                a.sets_number = :sets_number
                OR (
                  :related_cases IS NOT NULL
                  AND :related_cases != ''
                  AND a.related_cases = :related_cases
                )
              )
            ORDER BY a.testing_datetime ASC, a.last_name ASC, a.first_name ASC
            """
        )

        rows = conn.execute(
            parties_q,
            {
                "anchor_key": appointment_key,
                "day": day,
                "sets_number": sets_number,
                "related_cases": related_cases,
            },
        ).mappings().all()

    related = []
    for row in rows:
        data = dict(row)
        data["is_anchor"] = data.get("appointment_key") == appointment_key
        data["party_name"] = f"{data.get('first_name','')} {data.get('last_name','')}".strip()
        data["arrival_status"] = data.get("arrival_status") or "UNKNOWN"
        data["identity_verified_flag"] = int(data.get("identity_verified_flag") or 0)
        data["coc_included_flag"] = int(data.get("coc_included_flag") or 1)
        related.append(data)
    return related


def update_related_party_status(
    engine: Engine,
    appointment_key: str,
    related_appointment_key: str,
    arrival_status: str,
    identity_verified_flag: bool,
    coc_included_flag: bool,
    updated_by: str,
) -> None:
    status = str(arrival_status).strip().upper()
    if status not in VALID_ARRIVAL_STATUSES:
        raise ValueError(f"Invalid arrival status: {arrival_status}")

    payload = {
        "status_id": str(uuid.uuid4()),
        "appointment_key": appointment_key,
        "related_appointment_key": related_appointment_key,
        "arrival_status": status,
        "identity_verified_flag": 1 if identity_verified_flag else 0,
        "coc_included_flag": 1 if coc_included_flag else 0,
        "updated_by": updated_by,
        "updated_time": _now(),
    }

    with engine.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT status_id
                FROM gt_related_party_status
                WHERE appointment_key=:appointment_key
                  AND related_appointment_key=:related_appointment_key
                """
            ),
            {
                "appointment_key": appointment_key,
                "related_appointment_key": related_appointment_key,
            },
        ).mappings().one_or_none()

        if existing:
            conn.execute(
                text(
                    """
                    UPDATE gt_related_party_status
                    SET arrival_status=:arrival_status,
                        identity_verified_flag=:identity_verified_flag,
                        coc_included_flag=:coc_included_flag,
                        updated_by=:updated_by,
                        updated_time=:updated_time
                    WHERE appointment_key=:appointment_key
                      AND related_appointment_key=:related_appointment_key
                    """
                ),
                payload,
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO gt_related_party_status (
                        status_id, appointment_key, related_appointment_key, party_role,
                        arrival_status, identity_verified_flag, coc_included_flag,
                        updated_by, updated_time
                    ) VALUES (
                        :status_id, :appointment_key, :related_appointment_key, NULL,
                        :arrival_status, :identity_verified_flag, :coc_included_flag,
                        :updated_by, :updated_time
                    )
                    """
                ),
                payload,
            )
