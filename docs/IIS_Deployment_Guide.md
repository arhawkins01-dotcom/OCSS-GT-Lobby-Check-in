# IIS Deployment Guide (Reverse Proxy) — OCSS GT LOBBY Check-In

Recommended pattern:
- IIS provides HTTPS endpoint
- Streamlit runs as a Windows Service on a fixed port (example 8502)
- IIS reverse proxies to http://localhost:8502

Suggested paths:
- /gt-kiosk
- /gt-staff
- /gt-admin
