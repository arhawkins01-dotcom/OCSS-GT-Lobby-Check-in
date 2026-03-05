"""
database_service.py
-------------------
Manages the SQLite database connection and provides low-level query helpers.
All higher-level services import from this module.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "app_config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    config = _load_config()
    raw_path = config["database"]["path"]
    base = Path(__file__).parent.parent
    return base / raw_path


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create tables and indexes from schema.sql if they do not yet exist."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
        with open(schema_path, "r", encoding="utf-8") as fh:
            conn.executescript(fh.read())
        conn.commit()
    logger.info("Database initialised at %s", db_path)


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row_factory set to sqlite3.Row."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT query and return results as a list of dicts."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_write(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE statement. Returns lastrowid."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid


def execute_many(sql: str, params_list: list[tuple]) -> int:
    """Execute a statement for each item in params_list. Returns rowcount."""
    with get_connection() as conn:
        cursor = conn.executemany(sql, params_list)
        return cursor.rowcount
