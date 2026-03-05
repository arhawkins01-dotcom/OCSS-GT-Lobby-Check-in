from __future__ import annotations
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy import text
from sqlalchemy.engine import Engine

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def find_today_match(engine: Engine, sets_number: str, last_name: str) -> list[dict]:
    """Legacy function - finds appointments for today only"""
    sets_number = str(sets_number).strip()
    last_name = str(last_name).strip().lower()
    today = date.today().strftime("%Y-%m-%d")
    q = text("""
        SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
               a.status_from_onbase, a.part_type, a.assigned_to, v.current_status, v.checkin_time
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

def find_gt_appointments_for_checkin(engine: Engine, sets_number: str = None, 
                                      first_name: str = None, last_name: str = None) -> list[dict]:
    """
    Find all GT appointments for a client that are eligible for check-in.
    
    Important: Clients/case parties may have MULTIPLE CASES they are testing for.
    For example, a PPF (Presumed Parent Father) may have multiple cases with different
    CPM (Custodial Parent Mothers) and CHD (Children).
    
    Each case typically has 2 appointments ~14 days apart, but a person may have 
    multiple cases, resulting in many appointments.
    
    Check-in eligibility:
    - Appointments on or after today (future appointments)
    - Appointments today
    - Past appointments within 30 days (for late check-ins)
    
    The system will show all eligible appointments and let the user select
    which specific appointment/case they're checking in for.
    
    Args:
        sets_number: SETS number (if available)
        first_name: First name (required if no SETS number)
        last_name: Last name (required)
    
    Returns:
        List of eligible appointments with metadata and labeling
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Build query based on available identifiers
    if sets_number and sets_number.strip():
        sets_number = str(sets_number).strip()
        last_name = str(last_name).strip().lower()
        
        # Find all appointments for this SETS number
        q = text("""
            SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
                   a.status_from_onbase, a.part_type, a.assigned_to, a.appointment_type,
                   a.related_cases, v.current_status, v.checkin_time, v.completed_time
            FROM gt_appointments a
            JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
            WHERE a.sets_number=:sets
              AND lower(coalesce(a.last_name,''))=:lname
            ORDER BY a.testing_datetime ASC
        """)
        
        with engine.begin() as conn:
            rows = conn.execute(q, {"sets": sets_number, "lname": last_name}).mappings().all()
    else:
        # Search by name only
        if not first_name or not last_name:
            return []
        
        first_name = str(first_name).strip().lower()
        last_name = str(last_name).strip().lower()
        
        q = text("""
            SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
                   a.status_from_onbase, a.part_type, a.assigned_to, a.appointment_type,
                   a.related_cases, v.current_status, v.checkin_time, v.completed_time
            FROM gt_appointments a
            JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
            WHERE lower(coalesce(a.first_name,''))=:fname
              AND lower(coalesce(a.last_name,''))=:lname
            ORDER BY a.testing_datetime ASC
        """)
        
        with engine.begin() as conn:
            rows = conn.execute(q, {"fname": first_name, "lname": last_name}).mappings().all()
    
    appointments = [dict(r) for r in rows]
    
    # Filter out cancelled appointments
    appointments = [a for a in appointments 
                   if str(a.get("status_from_onbase", "")).lower() not in ["cancelled", "canceled"]]
    
    if not appointments:
        return []
    
    eligible_appointments = []
    
    # Process all appointments for eligibility
    for appt in appointments:
        appt_date = datetime.fromisoformat(str(appt["testing_datetime"])).date()
        
        # Check eligibility window: within 30 days in the past, or today/future
        if appt_date >= thirty_days_ago:
            # Build appointment label based on appointment_type and part_type
            appt_type = str(appt.get("appointment_type", "")).strip()
            part_type = str(appt.get("part_type", "")).strip()
            related_cases = str(appt.get("related_cases", "")).strip()
            
            # Create descriptive label
            if appt_type.lower() in ["first", "second"]:
                label = f"{appt_type} GT Appointment"
            else:
                label = "GT Appointment"
            
            if part_type:
                label += f" ({part_type})"
            
            if related_cases and related_cases.lower() != "none" and related_cases != "":
                label += f" - Case: {related_cases}"
            
            appt["appointment_label"] = label
            
            # Add timing indicator
            if appt_date < today:
                appt["timing_status"] = "Past (within 30 days)"
            elif appt_date == today:
                appt["timing_status"] = "Today"
            else:
                appt["timing_status"] = "Upcoming"
            
            eligible_appointments.append(appt)
    
    return eligible_appointments

def find_by_name_for_checkin(engine: Engine, first_name: str, last_name: str) -> list[dict]:
    """Find appointments by name for check-in - searches today's appointments"""
    today = date.today().strftime("%Y-%m-%d")
    q = text("""
    SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.last_name, a.first_name,
           a.status_from_onbase, a.part_type, a.assigned_to, v.current_status
    FROM gt_appointments a
    JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
    WHERE substr(a.testing_datetime,1,10) = :day
      AND LOWER(a.first_name) = LOWER(:first_name)
      AND LOWER(a.last_name) = LOWER(:last_name)
    """)
    
    with engine.begin() as conn:
        rows = conn.execute(q, {"day": today, "first_name": first_name.strip(), "last_name": last_name.strip()}).mappings().all()
    
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

def reconcile_future_appointments(engine: Engine, appointment_key: str) -> list[dict]:
    """
    Reconcile future appointments when a client checks in.
    
    When a client/case party checks in, we need to identify and reconcile
    any future appointments they have scheduled. This helps staff:
    - Know if the client has additional appointments coming up
    - Verify correct appointment selection
    - Prepare for future visits
    
    Returns:
        List of future appointments for the same SETS number
    """
    from datetime import date
    
    today = date.today()
    
    # Get info about the current appointment
    with engine.begin() as conn:
        current = conn.execute(text("""
            SELECT sets_number, testing_datetime, first_name, last_name
            FROM gt_appointments
            WHERE appointment_key = :key
        """), {"key": appointment_key}).mappings().first()
    
    if not current:
        return []
    
    sets_number = current["sets_number"]
    current_datetime = datetime.fromisoformat(str(current["testing_datetime"]))
    
    # Find all future appointments for this SETS number
    with engine.begin() as conn:
        future_appts = conn.execute(text("""
            SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
                   a.part_type, a.appointment_type, a.related_cases, a.assigned_to,
                   v.current_status
            FROM gt_appointments a
            JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
            WHERE a.sets_number = :sets
              AND a.testing_datetime > :current_dt
              AND a.appointment_key != :key
            ORDER BY a.testing_datetime ASC
        """), {"sets": sets_number, "current_dt": current_datetime.strftime("%Y-%m-%d %H:%M:%S"), "key": appointment_key}).mappings().all()
    
    future_appointments = [dict(r) for r in future_appts]
    
    # Record reconciliation event for each future appointment
    if future_appointments:
        for appt in future_appointments:
            record_event(
                engine, 
                appt["appointment_key"], 
                "RECONCILIATION_NOTED",
                performed_by="SYSTEM",
                notes=f"Client checked in for earlier appointment ({appointment_key}) - future appointment reconciled"
            )
    
    return future_appointments

def kiosk_checkin(engine: Engine, appointment_key: str) -> dict:
    """
    Process kiosk check-in and reconcile future appointments.
    
    Returns:
        Dictionary with check-in info and future appointments
    """
    # Perform check-in
    set_status(engine, appointment_key, "CHECKED_IN", performed_by="KIOSK")
    
    # Reconcile future appointments
    future_appointments = reconcile_future_appointments(engine, appointment_key)
    
    # Get current appointment info for notification
    with engine.begin() as conn:
        current = conn.execute(text("""
            SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
                   a.part_type, a.appointment_type, a.assigned_to,
                   v.checkin_time
            FROM gt_appointments a
            JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
            WHERE a.appointment_key = :key
        """), {"key": appointment_key}).mappings().first()
    
    return {
        "appointment_key": appointment_key,
        "checkin_time": current["checkin_time"] if current else None,
        "future_appointments_count": len(future_appointments),
        "future_appointments": future_appointments,
        "sets_number": current["sets_number"] if current else None,
        "name": f"{current['first_name']} {current['last_name']}" if current else None
    }
