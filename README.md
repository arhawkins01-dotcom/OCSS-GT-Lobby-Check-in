# OCSS GT Lobby Check-In

Companion application to Hyland OnBase genetic testing appointment scheduling.

## Features

| Feature | Description |
|---|---|
| **Kiosk check-in** | Patient enters SETS Number + Last Name to self-check-in |
| **Staff queue view** | Start / Complete buttons for CHECKED_IN → IN_PROCESS → COMPLETED workflow |
| **No-show flagging** | Staff flag SCHEDULED patients; admin finalises with one click |
| **OnBase sync-back** | Generates `GT_RESULTS_YYYYMMDD_HHMMSS.csv` for CSV Drop to OUTBOX (Method A) |

## Screenshots

### Kiosk — Patient Check-In
![Kiosk check-in](https://github.com/user-attachments/assets/33e433df-c242-423e-a3f9-f1e56d08417b)

### Kiosk — Successful Check-In
![Check-in success](https://github.com/user-attachments/assets/2e9e953b-36d5-409c-aaa3-9ebb414a2adb)

### Admin Panel — Load Export & Appointment Overview
![Admin panel](https://github.com/user-attachments/assets/45278d97-1e21-40bf-ad54-f0cbdeecc523)

## OnBase Schema

All 11 OnBase columns are used exactly as specified:

```
appointment_key, sets_number, testing_datetime, final_status,
checkin_time, in_process_time, completed_time, no_show_time,
last_updated_by, last_updated_time, notes
```

**Status values:** `SCHEDULED` · `CHECKED_IN` · `IN_PROCESS` · `COMPLETED` · `NO_SHOW`

**Datetime format:** `M/D/YYYY H:MM` (e.g. `3/5/2026 9:00`)

**Sync-back filename:** `GT_RESULTS_YYYYMMDD_HHMMSS.csv`

**Matching rule:** `appointment_key` (primary) — `sets_number` + `testing_datetime` (fallback)

> `appointment_key` is auto-generated on import when absent: `{sets_number}_{YYYYMMDDHHmm}`

## Run (local / dev)

```bash
pip install -r requirements.txt
streamlit run app/main_app.py
```

## Test

1. Go to **🔧 Admin** → **1. Load OnBase Export**
2. Upload `data/sample_onbase_export.csv`
3. Switch to **🏥 Kiosk** and check in with SETS `4012345`
4. Switch to **📋 Staff Queue** → click **▶ Start** then **✅ Complete**
5. Return to **🔧 Admin** → **5. Generate OnBase Sync-Back File** → click **📤 Drop to OUTBOX**

The resulting file in `outbox/` will be named `GT_RESULTS_YYYYMMDD_HHMMSS.csv` and contain all 11 OnBase columns with updated statuses.

## Project Structure

```
app/
  main_app.py          # Streamlit entry point (sidebar navigation)
  utils/
    state.py           # Session-state management + workflow mutators
    onbase.py          # OnBase CSV parsing + GT_RESULTS sync-back generation
  views/
    kiosk.py           # Patient self check-in page
    staff_queue.py     # Staff queue (Start / Complete)
    admin.py           # Admin: load export, no-show flagging, sync-back
data/
  sample_onbase_export.csv   # Sample data matching the OnBase schema
outbox/                      # Drop target for GT_RESULTS_*.csv files
requirements.txt
```
