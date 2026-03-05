# OCSS GT LOBBY Check-In

Companion application to Hyland OnBase genetic testing appointment scheduling.

## Features
- **Kiosk Check-In**: Support for check-in with or without SETS number
  - Multiple cases support: Clients may have multiple cases (e.g., PPF testing for multiple children with different CPMs)
  - Flexible date range: Check-in available starting on appointment date up to 30 days after
  - Smart appointment selection: Shows all eligible appointments across all cases
- **Staff Queue View**: Start and Complete appointment processing
- **No-Show Management**: Candidate flagging with admin finalization
- **OnBase Sync**: CSV file generation for sync-back to OnBase (Method A: OUTBOX Drop)
- **Multi-Date Upload**: Admin can upload appointments from any date range (past, present, future)

## Check-In Logic

### Multiple Cases Per Client
Clients and case parties may have **multiple SETS cases** they are testing for:
- Example: A PPF (Presumed Parent Father) may have multiple cases with different CPM (Custodial Parent Mothers) and CHD (Children)
- Each case typically has 2 appointments scheduled ~14 days apart
- One person can have many appointments across multiple cases

### Check-In Eligibility Window
- ✅ Appointments on or after their scheduled date
- ✅ Appointments within 30 days past their scheduled date (for late check-ins)
- ✅ System shows all eligible appointments and lets clients select the specific appointment/case

### Date Range Support
- **Past Dates**: Historical appointments (within 30 days for late check-in)
- **Today**: Current day appointments
- **Future Dates**: Upcoming scheduled appointments

## Run (local/dev)
```bash
pip install -r requirements.txt
streamlit run app/main_app.py
```

## Test
Upload `data/sample_onbase_export.csv` in Admin: Load Export page
