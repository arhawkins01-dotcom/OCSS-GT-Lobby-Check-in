from __future__ import annotations
import uuid
from datetime import datetime, date
from sqlalchemy import text
from sqlalchemy.engine import Engine

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def find_today_match(engine: Engine, sets_number: str, last_name: str) -> list[dict]:
    sets_number = str(sets_number).strip()
    last_name = str(last_name).strip().lower()
    today = date.today().strftime("%Y-%m-%d")
    q = text("""
        SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
               a.status_from_onbase, v.current_status, v.checkin_time
        FROM gt_appointments a
        JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
        WHERE a.sets_number=:sets
          AND lower(coalesce(a.last_name,''))=:lname
          AND substr(a.testing_datetime,1,10)=:today
        ORDER BY a.testing_datetime ASC
    """)
    with engine.begin() as conn:
        rows = conn.execute(q, {"sets": sets_number, "lname": last_name, "today": today}).mappings().all()
    return [dict(r) for r in rows]

def record_event(engine: Engine, appointment_key: str, event_type: str, performed_by: str, notes: str|None=None):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO gt_events (event_id,appointment_key,event_type,event_time,performed_by,notes)
            VALUES (:id,:k,:t,:tm,:by,:n)
        """), {"id": str(uuid.uuid4()), "k": appointment_key, "t": event_type, "tm": _now(), "by": performed_by, "n": notes})

def set_status(engine: Engine, appointment_key: str, new_status: str, performed_by: str, notes: str|None=None):
    now = _now()
    ts_field = {"CHECKED_IN":"checkin_time","IN_PROCESS":"in_process_time","COMPLETED":"completed_time","NO_SHOW":"no_show_time"}.get(new_status)
    with engine.begin() as conn:
        if ts_field:
            conn.execute(text(f"""
                UPDATE gt_visit_status
                SET current_status=:s, {ts_field}=:tm, last_updated_by=:by, last_updated_time=:tm
                WHERE appointment_key=:k
            """), {"s": new_status, "tm": now, "by": performed_by, "k": appointment_key})
        else:
            conn.execute(text("""
                UPDATE gt_visit_status
                SET current_status=:s, last_updated_by=:by, last_updated_time=:tm
                WHERE appointment_key=:k
            """), {"s": new_status, "tm": now, "by": performed_by, "k": appointment_key})
    record_event(engine, appointment_key, new_status, performed_by, notes)

def kiosk_checkin(engine: Engine, appointment_key: str):
    set_status(engine, appointment_key, "CHECKED_IN", performed_by="KIOSK")
