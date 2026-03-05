"""
sync_service.py
---------------
Builds and writes the OnBase sync CSV file for a given appointment date.
"""

import csv
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "app_config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Build sync records
# ---------------------------------------------------------------------------

def build_sync_records(sync_date: date) -> list[dict]:
    """
    Query appointments and check-ins for sync_date and return a list of
    dicts matching the OnBase sync file column spec.
    """
    # Import here to avoid circular imports at module load time.
    from services.database_service import execute_query

    sql = """
        SELECT
            a.appointment_id,
            a.student_gt_id,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.counselor,
            ci.checkin_id,
            ci.checkin_timestamp,
            ci.checkout_timestamp,
            ci.checkin_status,
            ci.no_show_flag,
            ci.notes        AS checkin_notes
        FROM   appointments a
        LEFT JOIN check_ins ci
               ON ci.appointment_id = a.appointment_id
              AND DATE(ci.checkin_timestamp) = ?
        WHERE  a.appointment_date = ?
        ORDER  BY a.appointment_time
    """
    rows = execute_query(sql, (sync_date.isoformat(), sync_date.isoformat()))

    records: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        status = row.get("checkin_status") or "NoShow"
        no_show = "Y" if row.get("no_show_flag") else "N"

        records.append(
            {
                "sync_record_id": f"SYN-{idx:04d}",
                "appointment_id": row["appointment_id"],
                "student_gt_id": row["student_gt_id"],
                "check_in_timestamp": row.get("checkin_timestamp") or "",
                "check_out_timestamp": row.get("checkout_timestamp") or "",
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"],
                "appointment_type": row["appointment_type"],
                "counselor": row.get("counselor") or "",
                "checkin_status": status,
                "no_show_flag": no_show,
                "notes": row.get("checkin_notes") or "",
                "sync_date": sync_date.isoformat(),
            }
        )
    return records


# ---------------------------------------------------------------------------
# Write sync file
# ---------------------------------------------------------------------------

_SYNC_COLUMNS = [
    "sync_record_id",
    "appointment_id",
    "student_gt_id",
    "check_in_timestamp",
    "check_out_timestamp",
    "appointment_date",
    "appointment_time",
    "appointment_type",
    "counselor",
    "checkin_status",
    "no_show_flag",
    "notes",
    "sync_date",
]


def write_sync_file(records: list[dict], sync_date: date, output_dir: Optional[Path] = None) -> Path:
    """
    Write sync records to a CSV file.  Returns the path of the created file.
    """
    config = _load_config()

    if output_dir is None:
        base = Path(__file__).parent.parent
        output_dir = base / config["onbase"]["sync_output_dir"]

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = config["onbase"]["sync_filename_prefix"]
    filename = f"{prefix}_{timestamp}.csv"
    file_path = output_dir / filename

    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=_SYNC_COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    logger.info("Sync file written: %s (%d records)", file_path, len(records))
    return file_path


def generate_sync_file(sync_date: date, generated_by: str, output_dir: Optional[Path] = None) -> Path:
    """
    High-level function: build records, write the file, and log to sync_log.
    Returns the path of the created file.
    """
    from services.database_service import execute_write

    records = build_sync_records(sync_date)
    file_path = write_sync_file(records, sync_date, output_dir)

    # Log the sync event
    execute_write(
        """
        INSERT INTO sync_log (sync_date, generated_by, record_count, filename)
        VALUES (?, ?, ?, ?)
        """,
        (sync_date.isoformat(), generated_by, len(records), file_path.name),
    )

    return file_path
