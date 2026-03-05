from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import yaml
from datetime import date
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.sync_service import build_sync_dataframe, write_sync_file
from utils.auth_utils import get_user_role, role_selector_sidebar

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "app_config.yaml"

def load_engine_cfg():
    cfg = yaml.safe_load(open(CONFIG_PATH,"r",encoding="utf-8"))
    db_cfg = cfg["storage"]["db"]
    dbc = DBConfig(db_type=db_cfg.get("type","sqlite"),
                   sqlite_path=db_cfg.get("sqlite_path"),
                   sqlserver_connection_string=db_cfg.get("sqlserver_connection_string"))
    engine = build_engine(dbc)
    if dbc.db_type.lower()=="sqlite":
        init_sqlite_schema(engine)
    return engine, cfg

st.set_page_config(page_title="Admin: Generate OnBase Sync File", layout="wide", page_icon="🔄")

# Add role selector to sidebar
role_selector_sidebar()

if get_user_role() != "admin":
    st.markdown("""
        <div style="background: #f8d7da; border: 2px solid #dc3545; padding: 30px; border-radius: 10px; text-align: center;">
            <h2>🔒 Admin Access Required</h2>
            <p>This page is restricted to administrators only.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

engine, cfg = load_engine_cfg()

# Custom CSS
st.markdown("""
    <style>
    .sync-header {
        text-align: center;
        padding: 30px 20px;
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 12px;
        color: white;
        margin-bottom: 30px;
    }
    .sync-header h1 {
        margin: 0;
        font-size: 2.5em;
    }
    .sync-info {
        background: #d1ecf1;
        border: 2px solid #17a2b8;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .data-preview {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="sync-header">
        <h1>🔄 Generate OnBase Sync File</h1>
        <p>Export completed appointments to CSV for OnBase integration</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("### 📅 Select Date")
day = st.date_input("Day", value=date.today()).strftime("%Y-%m-%d")

st.markdown("""
    <div class="sync-info">
        <strong>ℹ️ About Sync Files</strong><br>
        This tool generates a CSV file containing all appointment status updates for the selected date.
        The file will be written to the configured OUTBOX directory for OnBase to pick up and process.
    </div>
""", unsafe_allow_html=True)

df = build_sync_dataframe(engine, day)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Records", len(df))
with col2:
    completed = len(df[df.get('current_status') == 'COMPLETED']) if 'current_status' in df.columns else 0
    st.metric("Completed", completed)
with col3:
    no_shows = len(df[df.get('current_status') == 'NO_SHOW']) if 'current_status' in df.columns else 0
    st.metric("No-Shows", no_shows)

st.markdown("---")
st.markdown("### 📊 Data Preview")
st.dataframe(df, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("📁 Write Sync File to OUTBOX", use_container_width=True, type="primary"):
        path = write_sync_file(df, cfg["paths"]["sync_outbox"])
        st.success(f"✅ File successfully written to: {path}")
        st.balloons()
