from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

@dataclass
class DBConfig:
    db_type: str
    sqlite_path: Optional[str] = None
    sqlserver_connection_string: Optional[str] = None

def build_engine(cfg: DBConfig) -> Engine:
    if cfg.db_type.lower() == "sqlite":
        assert cfg.sqlite_path
        os.makedirs(os.path.dirname(cfg.sqlite_path), exist_ok=True)
        return create_engine(f"sqlite:///{cfg.sqlite_path}", future=True)
    if cfg.db_type.lower() == "sqlserver":
        assert cfg.sqlserver_connection_string
        return create_engine(cfg.sqlserver_connection_string, future=True, pool_pre_ping=True)
    raise ValueError(f"Unsupported db type: {cfg.db_type}")

def init_sqlite_schema(engine: Engine) -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS gt_appointments (
      appointment_key TEXT PRIMARY KEY,
      status_from_onbase TEXT,
      testing_datetime TEXT NOT NULL,
      sets_number TEXT NOT NULL,
      p_number TEXT,
      related_cases TEXT,
      part_type TEXT,
      first_name TEXT,
      last_name TEXT,
      appointment_type TEXT,
      location TEXT,
      test_type TEXT,
      coc TEXT,
      pre_call TEXT,
      assigned_to TEXT,
      scheduled_by TEXT,
      created_date TEXT,
      export_batch_id TEXT,
      mobile_phone TEXT,
      email_address TEXT,
      preferred_contact_method TEXT DEFAULT 'none',
      sms_opt_in INTEGER DEFAULT 0,
      email_opt_in INTEGER DEFAULT 0,
      last_sms_sent_at TEXT,
      last_email_sent_at TEXT,
      sms_status TEXT,
      email_status TEXT,
      notification_error TEXT,
      late_flag INTEGER DEFAULT 0,
      wait_minutes INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS gt_visit_status (
      appointment_key TEXT PRIMARY KEY,
      current_status TEXT NOT NULL,
      checkin_time TEXT,
      in_process_time TEXT,
      completed_time TEXT,
      no_show_time TEXT,
      last_updated_by TEXT,
      last_updated_time TEXT
    );
    CREATE TABLE IF NOT EXISTS gt_events (
      event_id TEXT PRIMARY KEY,
      appointment_key TEXT NOT NULL,
      event_type TEXT NOT NULL,
      event_time TEXT NOT NULL,
      performed_by TEXT,
      notes TEXT
    );
    CREATE TABLE IF NOT EXISTS coc_forms (
      coc_id TEXT PRIMARY KEY,
      appointment_key TEXT NOT NULL,
      sets_case_number TEXT,
      p_number TEXT,
      participant_name TEXT,
      participant_role TEXT,
      appointment_datetime TEXT,
      checkin_time TEXT,
      location TEXT,
      test_type TEXT,
      collector_name TEXT,
      collector_id TEXT,
      staff_user TEXT,
      generated_by TEXT,
      generated_at TEXT,
      document_ref TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      status TEXT DEFAULT 'DRAFT',
      notes TEXT,
      FOREIGN KEY(appointment_key) REFERENCES gt_appointments(appointment_key)
    );
    CREATE TABLE IF NOT EXISTS gt_related_party_status (
      status_id TEXT PRIMARY KEY,
      appointment_key TEXT NOT NULL,
      related_appointment_key TEXT NOT NULL,
      party_role TEXT,
      arrival_status TEXT NOT NULL DEFAULT 'UNKNOWN',
      identity_verified_flag INTEGER NOT NULL DEFAULT 0,
      coc_included_flag INTEGER NOT NULL DEFAULT 1,
      updated_by TEXT,
      updated_time TEXT,
      UNIQUE(appointment_key, related_appointment_key)
    );
    CREATE TABLE IF NOT EXISTS gt_notification_log (
      log_id TEXT PRIMARY KEY,
      appointment_key TEXT NOT NULL,
      channel TEXT NOT NULL,
      status TEXT NOT NULL,
      provider TEXT,
      sent_at TEXT,
      error_message TEXT,
      response_payload TEXT,
      event_type TEXT,
      performed_by TEXT
    );
    """
    with engine.begin() as conn:
        for stmt in schema.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

        # Additive migrations for existing SQLite DBs.
        _ensure_column(conn, "gt_appointments", "p_number", "TEXT")
        _ensure_column(conn, "gt_appointments", "location", "TEXT")
        _ensure_column(conn, "gt_appointments", "test_type", "TEXT")
        _ensure_column(conn, "gt_appointments", "mobile_phone", "TEXT")
        _ensure_column(conn, "gt_appointments", "email_address", "TEXT")
        _ensure_column(conn, "gt_appointments", "preferred_contact_method", "TEXT DEFAULT 'none'")
        _ensure_column(conn, "gt_appointments", "sms_opt_in", "INTEGER DEFAULT 0")
        _ensure_column(conn, "gt_appointments", "email_opt_in", "INTEGER DEFAULT 0")
        _ensure_column(conn, "gt_appointments", "last_sms_sent_at", "TEXT")
        _ensure_column(conn, "gt_appointments", "last_email_sent_at", "TEXT")
        _ensure_column(conn, "gt_appointments", "sms_status", "TEXT")
        _ensure_column(conn, "gt_appointments", "email_status", "TEXT")
        _ensure_column(conn, "gt_appointments", "notification_error", "TEXT")
        _ensure_column(conn, "gt_appointments", "late_flag", "INTEGER DEFAULT 0")
        _ensure_column(conn, "gt_appointments", "wait_minutes", "INTEGER DEFAULT 0")

        _ensure_column(conn, "coc_forms", "sets_case_number", "TEXT")
        _ensure_column(conn, "coc_forms", "p_number", "TEXT")
        _ensure_column(conn, "coc_forms", "participant_name", "TEXT")
        _ensure_column(conn, "coc_forms", "participant_role", "TEXT")
        _ensure_column(conn, "coc_forms", "appointment_datetime", "TEXT")
        _ensure_column(conn, "coc_forms", "checkin_time", "TEXT")
        _ensure_column(conn, "coc_forms", "location", "TEXT")
        _ensure_column(conn, "coc_forms", "test_type", "TEXT")
        _ensure_column(conn, "coc_forms", "staff_user", "TEXT")
        _ensure_column(conn, "coc_forms", "generated_by", "TEXT")
        _ensure_column(conn, "coc_forms", "generated_at", "TEXT")
        _ensure_column(conn, "coc_forms", "document_ref", "TEXT")


def _ensure_column(conn, table_name: str, column_name: str, column_def: str) -> None:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    existing = {str(r.get("name")) for r in rows}
    if column_name not in existing:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
