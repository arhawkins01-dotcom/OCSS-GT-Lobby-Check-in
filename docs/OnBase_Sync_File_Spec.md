# OnBase Sync File Specification

## Overview

At the end of each business day, the OCSS GT Lobby Check-In system generates a **sync CSV file** that is uploaded to OnBase to update appointment records with check-in outcomes.

---

## File Naming Convention

```
OCSS_GT_Sync_YYYYMMDD_HHMMSS.csv
```

Example: `OCSS_GT_Sync_20240315_173000.csv`

---

## File Format

- **Encoding**: UTF-8 (no BOM)
- **Delimiter**: comma (`,`)
- **Line endings**: CRLF (`\r\n`)
- **Header row**: Yes (first row)
- **Date format**: `YYYY-MM-DD`
- **Time format**: `HH:MM:SS` (24-hour)
- **Boolean flags**: `Y` = true, `N` = false

---

## Column Definitions

| # | Column Name | Type | Required | Description |
|---|-------------|------|----------|-------------|
| 1 | `sync_record_id` | TEXT | Yes | Unique ID for this sync record (format `SYN-NNNN`) |
| 2 | `appointment_id` | TEXT | Yes | Matches `appointment_id` in OnBase |
| 3 | `student_gt_id` | TEXT | Yes | Georgia Tech student ID (format `gtNNNNNN`) |
| 4 | `check_in_timestamp` | DATETIME | No | `YYYY-MM-DD HH:MM:SS` – blank if no check-in occurred |
| 5 | `check_out_timestamp` | DATETIME | No | `YYYY-MM-DD HH:MM:SS` – blank if not yet checked out |
| 6 | `appointment_date` | DATE | Yes | `YYYY-MM-DD` |
| 7 | `appointment_time` | TIME | Yes | `HH:MM` |
| 8 | `appointment_type` | TEXT | Yes | E.g., `Academic Advising` |
| 9 | `counselor` | TEXT | No | Staff member's name |
| 10 | `checkin_status` | TEXT | Yes | `Waiting`, `In-Progress`, `Completed`, or `NoShow` |
| 11 | `no_show_flag` | TEXT | Yes | `Y` or `N` |
| 12 | `notes` | TEXT | No | Free-text notes |
| 13 | `sync_date` | DATE | Yes | Date the sync file was generated (`YYYY-MM-DD`) |

---

## Sample Record

```csv
sync_record_id,appointment_id,student_gt_id,check_in_timestamp,check_out_timestamp,appointment_date,appointment_time,appointment_type,counselor,checkin_status,no_show_flag,notes,sync_date
SYN-001,APT-001,gt123456,2024-03-15 08:55:12,2024-03-15 09:45:00,2024-03-15,09:00,Academic Advising,Dr. Smith,Completed,N,,2024-03-15
SYN-002,APT-003,gt345678,,,2024-03-15,10:00,Financial Aid,Mr. Williams,NoShow,Y,Student did not check in,2024-03-15
```

---

## Validation Rules

1. `appointment_id` must exist in the OnBase appointments database.
2. `student_gt_id` must match the GT ID on the appointment.
3. `check_in_timestamp` must be earlier than `check_out_timestamp` when both are present.
4. `no_show_flag` must be `Y` when `checkin_status` is `NoShow`.
5. `no_show_flag` must be `N` when `checkin_status` is `Completed`.

---

## Delivery

The sync file is placed in the directory configured by `onbase.sync_output_dir` in `config/app_config.yaml` (default: `data/sync_output/`). Staff download the file from the **Generate OnBase Sync File** page and upload it to OnBase via the standard document import interface.
