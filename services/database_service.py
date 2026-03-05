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
      related_cases TEXT,
      part_type TEXT,
      first_name TEXT,
      last_name TEXT,
      appointment_type TEXT,
      coc TEXT,
      pre_call TEXT,
      assigned_to TEXT,
      scheduled_by TEXT,
      created_date TEXT,
      export_batch_id TEXT
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
    """
    with engine.begin() as conn:
        for stmt in schema.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
