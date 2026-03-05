# IIS Deployment Guide – OCSS GT Lobby Check-In

This guide describes how to deploy the OCSS GT Lobby Check-In Streamlit application behind **Internet Information Services (IIS) 10** on Windows Server 2019.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Windows Server | 2019 or 2022 |
| IIS | 10 (enabled via Server Roles) |
| Application Request Routing (ARR) | 3.0 |
| URL Rewrite Module | 2.1 |
| Python | 3.11 (64-bit) |
| pip | Latest |

---

## 1 – Install Python & Create Virtual Environment

```powershell
# Install Python 3.11 (download from python.org or use winget)
winget install Python.Python.3.11

# Navigate to the application root
cd C:\inetpub\wwwroot\ocss-lobby

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 2 – Configure the Application

1. Copy `config/app_config.yaml` to the server and update paths as needed.
2. Initialise the database:

```powershell
python -c "from services.database_service import init_db; init_db()"
```

3. (Optional) Load seed data for testing:

```powershell
sqlite3 data/ocss_lobby.db < database/seed_data.sql
```

---

## 3 – Start Streamlit

Use the provided PowerShell script to start Streamlit as a background service:

```powershell
.\deployment\start_streamlit.ps1
```

The script starts Streamlit on `http://localhost:8501`.

To run as a Windows Service, use **NSSM** (Non-Sucking Service Manager):

```powershell
# Download NSSM from https://nssm.cc
nssm install OCSS-Lobby-Streamlit "C:\inetpub\wwwroot\ocss-lobby\venv\Scripts\python.exe"
nssm set OCSS-Lobby-Streamlit AppParameters "-m streamlit run app/main_app.py --server.port 8501 --server.headless true"
nssm set OCSS-Lobby-Streamlit AppDirectory "C:\inetpub\wwwroot\ocss-lobby"
nssm start OCSS-Lobby-Streamlit
```

---

## 4 – Enable IIS Modules

In **Server Manager → Add Roles and Features**:
- Web Server (IIS) → Web Server → Application Development → CGI

Download and install:
- [ARR 3.0](https://www.iis.net/downloads/microsoft/application-request-routing)
- [URL Rewrite 2.1](https://www.iis.net/downloads/microsoft/url-rewrite)

---

## 5 – Configure IIS Reverse Proxy

See `deployment/iis_reverse_proxy_config.md` for the full `web.config` snippet.

**Summary steps:**
1. Open **IIS Manager** → select the site (e.g., `Default Web Site`).
2. Open **Application Request Routing Cache** → Enable Proxy.
3. Add a URL Rewrite rule forwarding `/*` to `http://localhost:8501/{R:0}`.

---

## 6 – Firewall

Allow inbound traffic on port **443** (HTTPS) and **80** (HTTP redirect). Block direct access to port **8501** from outside the server.

```powershell
New-NetFirewallRule -DisplayName "OCSS Lobby HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 7 – SSL/TLS

Obtain a certificate from GT's institutional CA or Let's Encrypt and bind it to the IIS site on port 443.

---

## 8 – Verify Deployment

1. Navigate to `https://<server-hostname>/` in a browser.
2. The Streamlit application should load.
3. Check logs in the `logs/` directory if the app does not start.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 502 Bad Gateway | Streamlit is not running. Start with `start_streamlit.ps1`. |
| Permission denied on `data/` | Grant IIS `NETWORK SERVICE` account write permission on the `data/` folder. |
| Module import errors | Activate the virtual environment before running Streamlit. |
