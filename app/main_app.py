from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import yaml
from datetime import date
from sqlalchemy import text
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from utils.auth_utils import role_selector_sidebar, get_user_role

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "app_config.yaml"

@st.cache_resource
def get_engine_and_cfg():
    cfg = yaml.safe_load(open(CONFIG_PATH, "r", encoding="utf-8"))
    db_cfg = cfg["storage"]["db"]
    dbc = DBConfig(
        db_type=db_cfg.get("type","sqlite"),
        sqlite_path=db_cfg.get("sqlite_path"),
        sqlserver_connection_string=db_cfg.get("sqlserver_connection_string"),
    )
    engine = build_engine(dbc)
    if dbc.db_type.lower() == "sqlite":
        init_sqlite_schema(engine)
    return engine, cfg

def check_workflow_status(engine):
    """Check the status of workflow steps"""
    status = {
        'data_loaded': False,
        'appointments_today': 0,
        'checked_in': 0,
        'completed': 0,
        'no_shows': 0
    }
    
    try:
        today = date.today().strftime("%Y-%m-%d")
        q = text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN v.current_status = 'CHECKED_IN' THEN 1 ELSE 0 END) as checked_in,
            SUM(CASE WHEN v.current_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN v.current_status = 'NO_SHOW' THEN 1 ELSE 0 END) as no_shows
        FROM gt_appointments a
        JOIN gt_visit_status v ON v.appointment_key = a.appointment_key
        WHERE substr(a.testing_datetime,1,10) = :day
        """)
        
        with engine.begin() as conn:
            result = conn.execute(q, {"day": today}).fetchone()
            if result and result[0] > 0:
                status['data_loaded'] = True
                status['appointments_today'] = result[0]
                status['checked_in'] = result[1] or 0
                status['completed'] = result[2] or 0
                status['no_shows'] = result[3] or 0
    except:
        pass
    
    return status

def main():
    st.set_page_config(page_title="OCSS GT LOBBY Check-In", layout="wide", page_icon="🏥")
    engine, _cfg = get_engine_and_cfg()

    role_selector_sidebar()
    role = get_user_role()
    
    # Check workflow status
    workflow_status = check_workflow_status(engine)

    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            color: white;
            margin-bottom: 40px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .main-header h1 {
            margin: 0;
            font-size: 3em;
            font-weight: bold;
        }
        .main-header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        .role-badge {
            display: inline-block;
            padding: 8px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            margin-top: 15px;
            font-size: 1em;
        }
        .workflow-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid #667eea;
            margin: 15px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .workflow-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .workflow-card h3 {
            color: #667eea;
            margin-top: 0;
        }
        .info-banner {
            background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #17a2b8;
            margin: 20px 0;
        }
        .step-number {
            display: inline-block;
            width: 35px;
            height: 35px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 35px;
            font-weight: bold;
            margin-right: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(f"""
        <div class="main-header">
            <h1>🏥 OCSS GT Lobby Check-In System</h1>
            <p>Genetic Testing Appointment Management</p>
            <div class="role-badge">Current Role: {role.upper()}</div>
        </div>
    """, unsafe_allow_html=True)

    # Info banner
    st.markdown("""
        <div class="info-banner">
            <strong>ℹ️ Development Mode</strong><br>
            Use the Pages menu in the sidebar to navigate. For production deployment, replace role selection with IIS/AD authentication.
        </div>
    """, unsafe_allow_html=True)

    # Admin Workflow Section
    if role == "admin":
        st.markdown("### 🎯 Admin Workflow Dashboard")
        
        # Progress overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            status_icon = "✅" if workflow_status['data_loaded'] else "⏳"
            st.metric("Today's Appointments", workflow_status['appointments_today'], delta=status_icon)
        with col2:
            st.metric("Checked In", workflow_status['checked_in'])
        with col3:
            st.metric("Completed", workflow_status['completed'])
        with col4:
            st.metric("No-Shows", workflow_status['no_shows'])
        
        st.markdown("---")
        
        # Interactive workflow cards
        col1, col2 = st.columns(2)
        
        with col1:
            # Step 1: Load Export
            step1_status = "✅ Complete" if workflow_status['data_loaded'] else "⏳ Pending"
            step1_color = "#28a745" if workflow_status['data_loaded'] else "#ffc107"
            
            st.markdown(f"""
                <div class="workflow-card" style="border-left-color: {step1_color};">
                    <h3><span class="step-number" style="background: {step1_color};">1</span> Load Daily Export</h3>
                    <p><strong>Status:</strong> {step1_status}</p>
                    <p>Upload the OnBase daily export to populate today's appointments.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📁 Go to Import Page", key="btn_import", use_container_width=True, type="primary" if not workflow_status['data_loaded'] else "secondary"):
                st.switch_page("../pages/3_Admin_Export_Load.py")
            
            # Step 3: Manage Queue
            st.markdown(f"""
                <div class="workflow-card">
                    <h3><span class="step-number">3</span> Manage Staff Queue</h3>
                    <p><strong>Active:</strong> {workflow_status['appointments_today'] - workflow_status['completed'] - workflow_status['no_shows']} appointments</p>
                    <p>Monitor and assist with appointment processing.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("👥 Go to Staff Queue", key="btn_queue", use_container_width=True, disabled=not workflow_status['data_loaded']):
                st.switch_page("../pages/2_Staff_Queue.py")
        
        with col2:
            # Step 2: Monitor Check-ins
            st.markdown(f"""
                <div class="workflow-card">
                    <h3><span class="step-number">2</span> Patient Check-Ins</h3>
                    <p><strong>Progress:</strong> {workflow_status['checked_in']} / {workflow_status['appointments_today']}</p>
                    <p>Patients self-check-in at kiosk. Staff can assist if needed.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🖥️ View Kiosk Page", key="btn_kiosk", use_container_width=True):
                st.switch_page("../pages/1_Kiosk_CheckIn.py")
            
            # Step 4: Generate Sync
            step4_ready = workflow_status['completed'] > 0 or workflow_status['no_shows'] > 0
            step4_color = "#667eea" if step4_ready else "#6c757d"
            
            st.markdown(f"""
                <div class="workflow-card" style="border-left-color: {step4_color};">
                    <h3><span class="step-number" style="background: {step4_color};">4</span> Generate Sync File</h3>
                    <p><strong>Ready to sync:</strong> {workflow_status['completed'] + workflow_status['no_shows']} records</p>
                    <p>Export completed appointments back to OnBase.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 Go to Sync Generator", key="btn_sync", use_container_width=True, type="primary" if step4_ready else "secondary"):
                st.switch_page("../pages/5_Admin_Generate_OnBase_Sync_File.py")
        
        # Additional admin tools
        st.markdown("---")
        st.markdown("### 🛠️ Additional Admin Tools")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⚠️ No-Show Finalization", use_container_width=True):
                st.switch_page("../pages/4_Admin_NoShow_Finalization.py")
        with col2:
            st.button("📊 View Reports (Coming Soon)", use_container_width=True, disabled=True)
        with col3:
            st.button("⚙️ System Settings (Coming Soon)", use_container_width=True, disabled=True)
    
    # Staff/Kiosk workflow (simplified view)
    else:
        st.markdown("### 🚀 Quick Start Workflow")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
                <div class="workflow-card">
                    <h3><span class="step-number">1</span> Load Daily Export</h3>
                    <p><strong>Role:</strong> Admin</p>
                    <p>Upload the OnBase daily export or use the sample file: <code>data/sample_onbase_export.csv</code></p>
                    <p>📊 This populates the appointment database for the day.</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div class="workflow-card">
                    <h3><span class="step-number">3</span> Staff Queue Management</h3>
                    <p><strong>Role:</strong> Staff / Admin</p>
                    <p>View today's appointments, assist with check-ins, start appointments, and mark completions.</p>
                    <p>⚠️ Flag no-show candidates automatically.</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div class="workflow-card">
                    <h3><span class="step-number">2</span> Patient Check-In</h3>
                    <p><strong>Role:</strong> Kiosk</p>
                    <p>Patients check in using their SETS Number and Last Name at the kiosk interface.</p>
                    <p>✅ Self-service check-in with instant confirmation.</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div class="workflow-card">
                    <h3><span class="step-number">4</span> Generate Sync File</h3>
                    <p><strong>Role:</strong> Admin</p>
                    <p>Generate the OnBase sync file (CSV) and write it to the OUTBOX folder for system integration.</p>
                    <p>🔄 Export completed appointments back to OnBase.</p>
                </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
