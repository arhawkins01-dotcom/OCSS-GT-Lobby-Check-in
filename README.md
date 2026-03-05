# OCSS GT LOBBY Check-In

Companion application to Hyland OnBase genetic testing appointment scheduling.

## Features
- Kiosk check-in (SETS Number + Last Name)
- Staff queue view (Start / Complete)
- No-show candidate flagging + admin finalization
- OnBase sync-back file generation (Method A: CSV Drop to OUTBOX)

## Run (local/dev)
pip install -r requirements.txt
streamlit run app/main_app.py

## Test
Upload data/sample_onbase_export.csv in Admin: Load Export
