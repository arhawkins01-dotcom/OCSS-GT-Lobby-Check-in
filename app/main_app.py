"""
main_app.py
-----------
Entry point for the OCSS GT Lobby Check-In Streamlit application.

Run with:
    streamlit run app/main_app.py
"""

import logging
import sys
from pathlib import Path

import streamlit as st
import yaml

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so pages/ can import services/ and utils/
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    config_path = PROJECT_ROOT / "config" / "app_config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        log_cfg = config.get("logging", {})
        log_level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
        log_dir = PROJECT_ROOT / log_cfg.get("log_dir", "logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
    except Exception:
        log_level = logging.INFO
        log_file = PROJECT_ROOT / "logs" / "app.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )


_setup_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
from services.database_service import init_db  # noqa: E402

init_db()

# ---------------------------------------------------------------------------
# Streamlit app shell
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OCSS GT Lobby Check-In",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ OCSS GT Lobby Check-In System")
st.markdown(
    """
    Welcome to the **OCSS GT Lobby Check-In System**.

    Use the navigation in the sidebar to access the appropriate page:

    | Page | Who uses it |
    |------|-------------|
    | 🏛️ Kiosk Check-In | Students – self-service check-in |
    | 📋 Staff Queue | Front-desk staff – manage the queue |
    | ⚙️ Admin Export & Load | Administrators – import/export data |
    | 🚫 No-Show Finalization | Staff/Admin – finalize no-shows |
    | 🔄 Generate OnBase Sync File | Administrators – generate daily sync |
    """
)

st.info("Please select a page from the **sidebar** to get started.")
