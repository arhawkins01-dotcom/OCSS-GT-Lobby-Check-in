from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from utils.file_utils import ensure_dir, timestamped_filename
import os

SYNC_COLUMNS = [
  "appointment_key","sets_number","testing_datetime","final_status",
  "checkin_time","in_process_time","completed_time","no_show_time",
  "last_updated_by","last_updated_time","notes"
]

def build_sync_dataframe(engine: Engine, day: str) -> pd.DataFrame:
    q = text("""
        SELECT a.appointment_key, a.sets_number, a.testing_datetime,
               v.current_status as final_status,
               v.checkin_time, v.in_process_time, v.completed_time, v.no_show_time,
               v.last_updated_by, v.last_updated_time,
               '' as notes
        FROM gt_appointments a
        JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
        WHERE substr(a.testing_datetime,1,10)=:day
        ORDER BY a.testing_datetime ASC
    """)
    with engine.begin() as conn:
        rows = conn.execute(q, {"day": day}).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return pd.DataFrame(columns=SYNC_COLUMNS)
    for c in SYNC_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[SYNC_COLUMNS]

def write_sync_file(df: pd.DataFrame, outbox_path: str) -> str:
    ensure_dir(outbox_path)
    fname = timestamped_filename("GT_RESULTS","csv")
    path = os.path.join(outbox_path, fname)
    df.to_csv(path, index=False)
    return path
