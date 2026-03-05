# OnBase Sync File Specification (Method A — CSV Drop)

## File Naming
GT_RESULTS_YYYYMMDD_HHMMSS.csv

## Required Columns
appointment_key, sets_number, testing_datetime, final_status,
checkin_time, in_process_time, completed_time, no_show_time,
last_updated_by, last_updated_time, notes

## Matching Rule (Recommended)
1) Match by appointment_key
2) Else: sets_number + testing_datetime
