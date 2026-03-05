"""
auth_utils.py
-------------
Password hashing, verification, and Streamlit session-based login helpers.
"""

import logging
from pathlib import Path
from typing import Optional

import bcrypt
import streamlit as st
import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "roles_config.yaml"


def _load_roles_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given password."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    """Return True if plain_password matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

SESSION_KEY_USER = "auth_user"
SESSION_KEY_ROLE = "auth_role"


def login(username: str, password: str) -> bool:
    """
    Validate credentials against the database.
    On success, stores user info in Streamlit session state and returns True.
    """
    from services.database_service import execute_query

    rows = execute_query(
        "SELECT * FROM staff_users WHERE username = ? AND is_active = 1",
        (username.strip().lower(),),
    )
    if not rows:
        return False

    user = rows[0]
    if not verify_password(password, user["password_hash"]):
        return False

    st.session_state[SESSION_KEY_USER] = {
        "user_id": user["user_id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
        "role": user["role"],
    }
    st.session_state[SESSION_KEY_ROLE] = user["role"]

    # Update last_login
    from services.database_service import execute_write
    execute_write(
        "UPDATE staff_users SET last_login = datetime('now') WHERE user_id = ?",
        (user["user_id"],),
    )
    logger.info("User '%s' logged in", username)
    return True


def logout() -> None:
    """Clear authentication state from Streamlit session."""
    st.session_state.pop(SESSION_KEY_USER, None)
    st.session_state.pop(SESSION_KEY_ROLE, None)
    logger.info("User logged out")


def get_current_user() -> Optional[dict]:
    """Return the current logged-in user dict, or None."""
    return st.session_state.get(SESSION_KEY_USER)


def get_current_role() -> str:
    """Return the current role string (defaults to 'kiosk' when not logged in)."""
    config = _load_roles_config()
    return st.session_state.get(SESSION_KEY_ROLE, config.get("default_role", "kiosk"))


def require_role(required_role: str) -> bool:
    """
    Return True if the current user has the required role or higher.
    Role hierarchy: admin > staff > kiosk
    """
    hierarchy = {"kiosk": 0, "staff": 1, "admin": 2}
    current = get_current_role()
    return hierarchy.get(current, 0) >= hierarchy.get(required_role, 99)


def render_login_form() -> None:
    """Render a compact login form in the Streamlit sidebar."""
    with st.sidebar:
        if get_current_user():
            user = get_current_user()
            st.success(f"Logged in as **{user['first_name']} {user['last_name']}** ({user['role']})")
            if st.button("Logout"):
                logout()
                st.rerun()
        else:
            st.subheader("Staff Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                if login(username, password):
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
