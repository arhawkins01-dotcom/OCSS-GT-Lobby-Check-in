# OCSS GT Lobby Check-In

A Streamlit-based lobby check-in and queue-management system for the **Georgia Tech Office of Civil and Systems Services (OCSS)**.

## Features

- 🏛️ **Kiosk Check-In** – Students self-check-in by GT ID or name
- 📋 **Staff Queue** – Real-time queue view for front-desk staff
- ⚙️ **Admin Export & Load** – Load appointments from OnBase CSV; export check-in records
- 🚫 **No-Show Finalization** – Mark no-show appointments at end of day
- 🔄 **OnBase Sync File** – Generate daily sync CSV for upload to OnBase

## Quick Start

```bash
# 1. Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Initialise the database
python -c "from services.database_service import init_db; init_db()"

# 3. (Optional) Load sample data
sqlite3 data/ocss_lobby.db < database/seed_data.sql

# 4. Start the application
streamlit run app/main_app.py
```

Then open `http://localhost:8501` in your browser.

## Project Structure

```
OCSS_GT_Lobby_CheckIn/
├── README.md
├── requirements.txt
├── .gitignore
├── config/                 # YAML configuration files
├── data/                   # Database and sample data files
├── database/               # SQL schema and seed data
├── docs/                   # Documentation
├── services/               # Business logic services
├── utils/                  # Shared utility modules
├── pages/                  # Streamlit multi-page app pages
├── app/                    # Main Streamlit entry point
└── deployment/             # IIS deployment scripts and config
```

## Documentation

See the `docs/` directory for:
- [System Overview](docs/OCSS_GT_LOBBY_CheckIn_System_Overview.md)
- [IIS Deployment Guide](docs/IIS_Deployment_Guide.md)
- [OnBase Sync File Spec](docs/OnBase_Sync_File_Spec.md)
- [Staff User Guide](docs/Staff_User_Guide.md)
- [Kiosk Operating Procedure](docs/Kiosk_Operating_Procedure.md)

## Tech Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit |
| Language | Python 3.11 |
| Database | SQLite 3 |
| Auth | bcrypt |
| Config | PyYAML |
| Deployment | Windows Server / IIS 10 |
