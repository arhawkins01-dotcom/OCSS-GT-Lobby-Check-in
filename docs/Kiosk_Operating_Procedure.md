# Kiosk Operating Procedure – OCSS GT Lobby Check-In

## Purpose

This document describes the daily procedures for setting up, operating, and shutting down the **OCSS GT Lobby Check-In Kiosk**.

---

## Equipment

- Dedicated kiosk workstation (Windows 10/11 or Windows Server 2019)
- Touchscreen monitor (recommended: 21" or larger)
- Optional: USB barcode / GT ID card scanner

---

## Daily Start-Up Procedure

1. **Power on** the kiosk workstation.
2. The Streamlit application should **auto-start** via the configured Windows Service (`OCSS-Lobby-Streamlit`). Allow 30–60 seconds for it to load.
3. Open the kiosk browser (Microsoft Edge in Kiosk Mode is recommended):
   - Press `Win + R`, type:
     ```
     msedge.exe --kiosk http://localhost:8501/Kiosk_CheckIn --edge-kiosk-type=fullscreen
     ```
4. Verify the **Kiosk Check-In** page is displayed and shows today's date.
5. If the page does not load, see the **Troubleshooting** section below.

---

## Normal Operation

### Student Self Check-In
1. Student approaches the kiosk.
2. Student enters their **GT ID** (e.g., `gt123456`) in the text field.
   - Alternatively, the student may enter their **first and last name** if they do not know their GT ID.
3. The system searches for a scheduled appointment for today.
4. If found, the student confirms their name and appointment details and clicks **Check In**.
5. A **confirmation screen** is displayed with the student's name and estimated wait time.
6. The student takes a seat in the waiting area.

### No Appointment Found
If no appointment is found, the kiosk displays a message instructing the student to speak with front-desk staff.

---

## Kiosk Timeout

The kiosk screen automatically resets to the home screen after **60 seconds** of inactivity (configurable in `config/app_config.yaml` → `app.kiosk_timeout_seconds`).

---

## Daily Shut-Down Procedure

1. Ensure staff have finalized no-shows on the **No-Show Finalization** page.
2. Ensure the **OnBase Sync File** has been generated and uploaded.
3. Close the kiosk browser window (press `Ctrl+Alt+Del` to exit kiosk mode if needed).
4. The Streamlit service continues running in the background; **do not stop it** unless performing maintenance.
5. Power down the monitor if desired; the workstation may remain on.

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| Page shows "Connection refused" | Open PowerShell and run `.\deployment\start_streamlit.ps1`, or restart the `OCSS-Lobby-Streamlit` Windows Service. |
| Page loads but shows an error | Check `logs/app.log` for details. Contact IT support if unresolved. |
| GT ID not found | Verify with staff that the appointment was loaded in the system for today. |
| Touchscreen unresponsive | Restart the browser. If the problem persists, restart the workstation. |

---

## Emergency Contact

- **OCSS IT Help Desk**: `ocss-it@gatech.edu`
- **On-call technician**: See posted contact sheet at the front desk.
