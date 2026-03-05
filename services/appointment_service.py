from __future__ import annotations
import pandas as pd
import uuid
from sqlalchemy import text
from sqlalchemy.engine import Engine
from utils.validation_utils import validate_onbase_export

EXPECTED_COLS = [
    "Status","Testing Date/Time","SETS Number","Related Cases","Part Type",
    "First Name","Last Name","Appointment","COC","Pre-Call","Assigned To","Scheduled By","Created Date"
]

def load_onbase_export(file) -> pd.DataFrame:
    name = getattr(file, "name", "upload").lower()
    
    if name.endswith(".csv"):
        df = pd.read_csv(file, dtype={"SETS Number": str})
    else:
        # For Excel, read without dtype first, then convert SETS Number to string
        df = pd.read_excel(file)
        if "SETS Number" in df.columns:
            # Convert to string first, then strip .0 suffix
            df["SETS Number"] = df["SETS Number"].fillna("").astype(str)
            # Remove .0 from numeric strings (e.g., "1234567890.0" -> "1234567890")
            df["SETS Number"] = df["SETS Number"].apply(
                lambda x: x[:-2] if isinstance(x, str) and x.endswith(".0") else x
            )
    
    df.columns = [str(c).strip() for c in df.columns]
    # add missing expected cols
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = None
    df = df[EXPECTED_COLS]
    missing = validate_onbase_export(df)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df["Testing Date/Time"] = pd.to_datetime(df["Testing Date/Time"], errors="coerce")
    df["Created Date"] = pd.to_datetime(df["Created Date"], errors="coerce")
    return df

def generate_appointment_key(sets_number: str, testing_dt: pd.Timestamp) -> str:
    return f"{sets_number}_{testing_dt.strftime('%Y%m%d%H%M')}"

def ingest_export(engine: Engine, df: pd.DataFrame, export_batch_id: str | None = None) -> dict:
    """
    Ingest appointment export data into the database.
    Handles appointments from any date (past, present, future) to support:
    - Daily uploads with varying date ranges
    - Historical appointments (previous dates)
    - Current day appointments (today)
    - Future scheduled appointments
    
    Returns statistics about the ingestion including date range analysis.
    """
    from datetime import datetime, date
    
    export_batch_id = export_batch_id or str(uuid.uuid4())
    inserted, updated = 0, 0
    earliest_date = None
    latest_date = None
    today = date.today()
    past_count = 0
    today_count = 0
    future_count = 0
    
    with engine.begin() as conn:
        for _, r in df.iterrows():
            if pd.isna(r["Testing Date/Time"]):
                continue
            
            sets = str(r["SETS Number"]).strip() if not pd.isna(r["SETS Number"]) else ""
            
            # Clean up SETS number - remove .0 suffix if it's a float that was converted to string
            # (Excel stores numbers as floats, so "1234567890" becomes "1234567890.0")
            if sets and sets.endswith(".0"):
                sets = sets[:-2]
            
            # If no SETS, use name as part of key for uniqueness
            if not sets or sets.lower() == "nan":
                sets = ""
            
            appt_datetime = r["Testing Date/Time"]
            appt_date = appt_datetime.date()
            
            # Track date range
            if earliest_date is None or appt_date < earliest_date:
                earliest_date = appt_date
            if latest_date is None or appt_date > latest_date:
                latest_date = appt_date
            
            # Count by date category
            if appt_date < today:
                past_count += 1
            elif appt_date == today:
                today_count += 1
            else:
                future_count += 1
            
            # Generate appointment key - use name if no SETS number
            if sets:
                appt_key = generate_appointment_key(sets, r["Testing Date/Time"])
            else:
                # For records without SETS, create key from name + datetime
                first = str(r["First Name"]).strip() if not pd.isna(r["First Name"]) else "UNKNOWN"
                last = str(r["Last Name"]).strip() if not pd.isna(r["Last Name"]) else "UNKNOWN"
                appt_key = f"{first}_{last}_{r['Testing Date/Time'].strftime('%Y%m%d%H%M')}"
            payload = {
                "appointment_key": appt_key,
                "status_from_onbase": None if pd.isna(r["Status"]) else str(r["Status"]),
                "testing_datetime": r["Testing Date/Time"].strftime("%Y-%m-%d %H:%M:%S"),
                "sets_number": sets,
                "related_cases": None if pd.isna(r["Related Cases"]) else str(r["Related Cases"]),
                "part_type": None if pd.isna(r["Part Type"]) else str(r["Part Type"]),
                "first_name": None if pd.isna(r["First Name"]) else str(r["First Name"]),
                "last_name": None if pd.isna(r["Last Name"]) else str(r["Last Name"]),
                "appointment_type": None if pd.isna(r["Appointment"]) else str(r["Appointment"]),
                "coc": None if pd.isna(r["COC"]) else str(r["COC"]),
                "pre_call": None if pd.isna(r["Pre-Call"]) else str(r["Pre-Call"]),
                "assigned_to": None if pd.isna(r["Assigned To"]) else str(r["Assigned To"]),
                "scheduled_by": None if pd.isna(r["Scheduled By"]) else str(r["Scheduled By"]),
                "created_date": None if pd.isna(r["Created Date"]) else r["Created Date"].strftime("%Y-%m-%d %H:%M:%S"),
                "export_batch_id": export_batch_id,
            }
            exists = conn.execute(text("SELECT 1 FROM gt_appointments WHERE appointment_key=:k"), {"k": appt_key}).fetchone()
            if exists:
                conn.execute(text("""
                    UPDATE gt_appointments SET
                      status_from_onbase=:status_from_onbase,
                      testing_datetime=:testing_datetime,
                      sets_number=:sets_number,
                      related_cases=:related_cases,
                      part_type=:part_type,
                      first_name=:first_name,
                      last_name=:last_name,
                      appointment_type=:appointment_type,
                      coc=:coc,
                      pre_call=:pre_call,
                      assigned_to=:assigned_to,
                      scheduled_by=:scheduled_by,
                      created_date=:created_date,
                      export_batch_id=:export_batch_id
                    WHERE appointment_key=:appointment_key
                """), payload)
                updated += 1
            else:
                conn.execute(text("""
                    INSERT INTO gt_appointments (
                      appointment_key,status_from_onbase,testing_datetime,sets_number,related_cases,part_type,
                      first_name,last_name,appointment_type,coc,pre_call,assigned_to,scheduled_by,created_date,export_batch_id
                    ) VALUES (
                      :appointment_key,:status_from_onbase,:testing_datetime,:sets_number,:related_cases,:part_type,
                      :first_name,:last_name,:appointment_type,:coc,:pre_call,:assigned_to,:scheduled_by,:created_date,:export_batch_id
                    )
                """), payload)
                inserted += 1
            vs = conn.execute(text("SELECT 1 FROM gt_visit_status WHERE appointment_key=:k"), {"k": appt_key}).fetchone()
            if not vs:
                conn.execute(text("INSERT INTO gt_visit_status (appointment_key,current_status) VALUES (:k,'SCHEDULED')"), {"k": appt_key})
    
    return {
        "export_batch_id": export_batch_id, 
        "inserted": inserted, 
        "updated": updated,
        "earliest_date": earliest_date.strftime("%Y-%m-%d") if earliest_date else None,
        "latest_date": latest_date.strftime("%Y-%m-%d") if latest_date else None,
        "past_appointments": past_count,
        "today_appointments": today_count,
        "future_appointments": future_count,
        "total_processed": inserted + updated
    }
