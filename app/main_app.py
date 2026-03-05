"""
OCSS GT Lobby Check-In — Main Streamlit Application

Run:
    streamlit run app/main_app.py

Navigation (sidebar):
    • Kiosk      — Patient self check-in
    • Staff Queue — Staff start/complete view
    • Admin      — Load export, manage no-shows, generate sync-back
"""

import sys
import os

# Allow sibling imports (pages, utils) regardless of the working directory
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from views.kiosk import render as render_kiosk
from views.staff_queue import render as render_staff_queue
from views.admin import render as render_admin

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OCSS GT Lobby Check-In",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ─────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8b/Genetic_testing.jpg/320px-Genetic_testing.jpg",
        width=260,
    )
    st.title("OCSS GT Lobby")
    st.caption("Genetic Testing Check-In System")
    st.divider()

    page = st.radio(
        "Navigate to",
        options=["🏥 Kiosk", "📋 Staff Queue", "🔧 Admin"],
        label_visibility="collapsed",
    )

# ── Route to selected page ─────────────────────────────────────────────────
if page == "🏥 Kiosk":
    render_kiosk()
elif page == "📋 Staff Queue":
    render_staff_queue()
elif page == "🔧 Admin":
    render_admin()
