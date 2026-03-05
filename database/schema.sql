-- ============================================================
-- OCSS GT Lobby Check-In System – Database Schema
-- Compatible with SQLite 3
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Appointments
-- Loaded from OnBase export CSV by admin staff.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id       TEXT PRIMARY KEY,
    student_gt_id        TEXT NOT NULL,
    student_first_name   TEXT NOT NULL,
    student_last_name    TEXT NOT NULL,
    student_email        TEXT,
    appointment_date     TEXT NOT NULL,   -- ISO format YYYY-MM-DD
    appointment_time     TEXT NOT NULL,   -- HH:MM (24h)
    appointment_type     TEXT NOT NULL,
    counselor            TEXT,
    status               TEXT NOT NULL DEFAULT 'Scheduled',
    notes                TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_appt_date
    ON appointments (appointment_date);

CREATE INDEX IF NOT EXISTS idx_appt_student
    ON appointments (student_gt_id);

-- ------------------------------------------------------------
-- Check-Ins
-- Created when a student checks in via the kiosk.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS check_ins (
    checkin_id           TEXT PRIMARY KEY,
    appointment_id       TEXT NOT NULL REFERENCES appointments (appointment_id),
    student_gt_id        TEXT NOT NULL,
    checkin_timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
    checkout_timestamp   TEXT,
    checkin_status       TEXT NOT NULL DEFAULT 'Waiting',
    -- Possible values: Waiting | In-Progress | Completed | NoShow
    no_show_flag         INTEGER NOT NULL DEFAULT 0,
    no_show_finalized_by TEXT,
    no_show_finalized_at TEXT,
    notes                TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_checkin_date
    ON check_ins (checkin_timestamp);

CREATE INDEX IF NOT EXISTS idx_checkin_student
    ON check_ins (student_gt_id);

-- ------------------------------------------------------------
-- Staff Users
-- Stores staff and admin accounts.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff_users (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username             TEXT NOT NULL UNIQUE,
    password_hash        TEXT NOT NULL,   -- bcrypt hash
    first_name           TEXT NOT NULL,
    last_name            TEXT NOT NULL,
    email                TEXT NOT NULL UNIQUE,
    role                 TEXT NOT NULL DEFAULT 'staff',
    -- Possible values: staff | admin
    is_active            INTEGER NOT NULL DEFAULT 1,
    last_login           TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- OnBase Sync Log
-- Records each time a sync file is generated for audit purposes.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_log (
    sync_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_date            TEXT NOT NULL,
    generated_by         TEXT NOT NULL,
    record_count         INTEGER NOT NULL DEFAULT 0,
    filename             TEXT NOT NULL,
    generated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- Audit Log
-- Generic audit trail for significant system events.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    log_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type           TEXT NOT NULL,
    event_detail         TEXT,
    performed_by         TEXT,
    performed_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
