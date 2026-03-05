# OCSS GT Lobby Check-In System – System Overview

## Purpose

The **OCSS GT Lobby Check-In System** is a web-based kiosk and staff management application built with [Streamlit](https://streamlit.io/) for Georgia Tech's Office of Civil and Systems Services (OCSS). It replaces manual sign-in sheets and provides seamless integration with the OnBase document-management platform.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         IIS Reverse Proxy                           │
│                     (Windows Server – IIS 10)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP(S)
┌────────────────────────────▼────────────────────────────────────────┐
│               Streamlit Application (Python 3.11)                   │
│                                                                     │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │  Kiosk Page  │  │ Staff Queue │  │ Admin / Sync Pages       │  │
│  └──────┬───────┘  └──────┬──────┘  └───────────┬──────────────┘  │
│         └─────────────────┼─────────────────────┘                  │
│                    ┌──────▼──────┐                                  │
│                    │  Services   │                                  │
│                    │  (Python)   │                                  │
│                    └──────┬──────┘                                  │
│                    ┌──────▼──────┐                                  │
│                    │  SQLite DB  │                                  │
│                    └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Pages (`/pages/`)

| Page | File | Access |
|------|------|--------|
| Kiosk Check-In | `1_Kiosk_CheckIn.py` | Public (kiosk) |
| Staff Queue | `2_Staff_Queue.py` | Staff, Admin |
| Admin Export & Load | `3_Admin_Export_Load.py` | Admin |
| No-Show Finalization | `4_NoShow_Finalization.py` | Staff, Admin |
| Generate OnBase Sync File | `5_Generate_OnBase_Sync_File.py` | Admin |

### Services (`/services/`)

| Module | Responsibility |
|--------|---------------|
| `database_service.py` | SQLite connection management, raw query execution |
| `appointment_service.py` | CRUD operations for appointments |
| `checkin_service.py` | Check-in creation, status updates, queue queries |
| `sync_service.py` | Building and writing the OnBase sync CSV |

### Utils (`/utils/`)

| Module | Responsibility |
|--------|---------------|
| `auth_utils.py` | Password hashing, session-based login/logout |
| `validation_utils.py` | GT ID format validation, date/time checks |
| `file_utils.py` | CSV import/export helpers, OnBase file parsing |

---

## Data Flow

### Student Check-In Flow
1. Student arrives at the kiosk and enters their **GT ID** (or first/last name).
2. `checkin_service.lookup_appointment()` queries the `appointments` table.
3. If a matching appointment is found, `checkin_service.create_checkin()` inserts a row into `check_ins`.
4. The student's name appears in the **Staff Queue** page in real time.

### Appointment Load Flow
1. Admin exports appointments from **OnBase** as a CSV file matching the schema in `data/sample_onbase_export.csv`.
2. Admin uploads the CSV via the **Admin Export & Load** page.
3. `file_utils.parse_onbase_export()` validates and normalises rows.
4. `appointment_service.bulk_upsert_appointments()` inserts/updates the `appointments` table.

### OnBase Sync Flow
1. At end of day, admin opens the **Generate OnBase Sync File** page.
2. `sync_service.build_sync_records()` joins `appointments` and `check_ins` for the selected date.
3. A CSV file matching the spec in `docs/OnBase_Sync_File_Spec.md` is written to `data/sync_output/`.
4. Admin downloads the file and uploads it to OnBase manually (or via a scheduled task).

---

## Configuration

| File | Purpose |
|------|---------|
| `config/app_config.yaml` | Paths, UI settings, logging |
| `config/roles_config.yaml` | Role definitions and page permissions |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit 1.32+ |
| Language | Python 3.11 |
| Database | SQLite 3 |
| Config | YAML (PyYAML) |
| Auth | bcrypt |
| Data | pandas |
| Deployment | Windows Server 2019, IIS 10 |
