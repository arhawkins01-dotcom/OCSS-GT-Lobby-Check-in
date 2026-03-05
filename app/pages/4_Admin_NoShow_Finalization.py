from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import yaml
from datetime import date, datetime, timedelta
from sqlalchemy import text
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.checkin_service import set_status
from utils.auth_utils import get_user_role, role_selector_sidebar

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "app_config.yaml"

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

st.set_page_config(page_title="Admin: No-Show Finalization", layout="wide", page_icon="⚠️")

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
    .noshow-header {
        text-align: center;
        padding: 30px 20px;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 12px;
        color: white;
        margin-bottom: 30px;
    }
    .noshow-header h1 {
        margin: 0;
        font-size: 2.5em;
    }
    .warning-card {
        background: #fff3cd;
        border: 2px solid  #ffc107;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .candidate-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="noshow-header">
        <h1>⚠️ No-Show Finalization</h1>
        <p>Review and finalize no-show appointments</p>
    </div>
""", unsafe_allow_html=True)
today = date.today().strftime("%Y-%m-%d")
mins = int(cfg.get("no_show_rules",{}).get("minutes_after_appt_to_flag", 30))
now = datetime.now()

q = text("""
SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.first_name, a.last_name,
       v.current_status
FROM gt_appointments a
JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
WHERE substr(a.testing_datetime,1,10)=:day
ORDER BY a.testing_datetime ASC
""")
with engine.begin() as conn:
    rows = conn.execute(q, {"day": today}).mappings().all()
df = pd.DataFrame([dict(r) for r in rows])
if df.empty:
    st.warning("No appointments loaded for today.")
    st.stop()

def candidate(row):
    if row["current_status"] != "SCHEDULED":
        return False
    try:
        appt = datetime.fromisoformat(str(row["testing_datetime"]))
    except Exception:
        return False
    return now > appt + timedelta(minutes=mins)

cand = df[df.apply(candidate, axis=1)].copy()

st.markdown(f"""
    <div class="warning-card">
        <h3>⚠️ No-Show Candidates Detected</h3>
        <p>Found <strong>{len(cand)}</strong> appointment(s) that are more than <strong>{mins} minutes</strong> past their scheduled time and still marked as SCHEDULED.</p>
        <p>Review the list below and select appointments to finalize as NO_SHOW.</p>
    </div>
""", unsafe_allow_html=True)

if len(cand) == 0:
    st.success("✅ No no-show candidates found! All appointments are on track.")
else:
    st.markdown("### 📋 No-Show Candidates")
    st.dataframe(cand, use_container_width=True, hide_index=True, height=300)
    
    st.markdown("---")
    st.markdown("### 🎯 Finalize No-Shows")
    selected = st.multiselect("Select appointment(s) to finalize as NO_SHOW", 
                              cand["appointment_key"].tolist(),
                              format_func=lambda x: f"{x} - {cand[cand['appointment_key']==x].iloc[0]['first_name']} {cand[cand['appointment_key']==x].iloc[0]['last_name']}")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("⚠️ Finalize Selected as NO_SHOW", use_container_width=True, type="primary", disabled=len(selected)==0):
            for k in selected:
                set_status(engine, k, "NO_SHOW", performed_by="ADMIN", notes="Finalized no-show")
            st.success(f"✅ Finalized {len(selected)} appointment(s) as NO_SHOW.")
            st.rerun()
