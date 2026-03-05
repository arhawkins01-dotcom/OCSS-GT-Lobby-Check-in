from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path so we can import services and utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import yaml
from services.database_service import DBConfig, build_engine, init_sqlite_schema
from services.appointment_service import load_onbase_export, ingest_export
from utils.auth_utils import get_user_role, role_selector_sidebar

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "app_config.yaml"

def get_engine():
    cfg = yaml.safe_load(open(CONFIG_PATH,"r",encoding="utf-8"))
    db_cfg = cfg["storage"]["db"]
    dbc = DBConfig(db_type=db_cfg.get("type","sqlite"),
                   sqlite_path=db_cfg.get("sqlite_path"),
                   sqlserver_connection_string=db_cfg.get("sqlserver_connection_string"))
    engine = build_engine(dbc)
    if dbc.db_type.lower()=="sqlite":
        init_sqlite_schema(engine)
    return engine

st.set_page_config(page_title="Admin: Load Export", layout="wide")

# Add role selector to sidebar
role_selector_sidebar()

# Custom CSS styling
st.markdown("""
    <style>
    .admin-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #FF6B6B 0%, #DC3545 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 30px;
    }
    .admin-header h1 {
        margin: 0;
        font-size: 2.5em;
    }
    .upload-section {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 40px;
        border-radius: 15px;
        border: 3px dashed #667eea;
        text-align: center;
        margin: 30px 0;
        transition: all 0.3s ease;
    }
    .upload-section:hover {
        border-color: #764ba2;
        background: linear-gradient(135deg, #667eea25 0%, #764ba225 100%);
    }
    .upload-icon {
        font-size: 4em;
        margin-bottom: 20px;
    }
    .upload-title {
        font-size: 1.8em;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
    }
    .upload-subtitle {
        font-size: 1.1em;
        color: #666;
        margin-bottom: 20px;
    }
    .success-message {
        background: #d4edda;
        border: 2px solid #28a745;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .info-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 15px 0;
    }
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

current_role = get_user_role()
if current_role != "admin":
    st.markdown(f"""
        <div style="background: #f8d7da; border: 2px solid #dc3545; padding: 20px; border-radius: 10px; text-align: center;">
            <h3>🔒 Admin Access Required</h3>
            <p>Current role: <strong>{current_role}</strong></p>
            <p>Please change your role to <strong>"admin"</strong> in the sidebar to access this page.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# Admin header
st.markdown("""
    <div class="admin-header">
        <h1>📊 Admin: Load OnBase Export</h1>
        <p>Upload daily appointment exports from OnBase</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("### Upload Appointment Data")

# Drag and Drop Section
st.markdown("""
    <div class="upload-section">
        <div class="upload-icon">📁</div>
        <div class="upload-title">Drag & Drop Your File Here</div>
        <div class="upload-subtitle">or click to browse • CSV or Excel formats supported</div>
    </div>
""", unsafe_allow_html=True)

# File uploader with drag-and-drop
uploaded = st.file_uploader(
    "Choose file",
    type=["csv", "xlsx"],
    help="Upload the daily OnBase appointment export file",
    label_visibility="collapsed"
)

if uploaded is not None:
    try:
        st.markdown("---")
        st.markdown("### 📋 File Uploaded Successfully!")
        
        with st.spinner("Validating and processing file..."):
            df = load_onbase_export(uploaded)
        
        st.markdown("""
            <div class="success-message">
                ✅ <strong>File validated successfully!</strong> All required columns are present.
            </div>
        """, unsafe_allow_html=True)
        
        # Statistics cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="stats-card">
                    <h2>{len(df)}</h2>
                    <p>Total Records</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            unique_dates = df['testing_datetime'].nunique() if 'testing_datetime' in df.columns else 0
            st.markdown(f"""
                <div class="stats-card">
                    <h2>{unique_dates}</h2>
                    <p>Unique Dates</p>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            unique_patients = df['sets_number'].nunique() if 'sets_number' in df.columns else 0
            st.markdown(f"""
                <div class="stats-card">
                    <h2>{unique_patients}</h2>
                    <p>Patients</p>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="stats-card">
                    <h2>{uploaded.size // 1024}KB</h2>
                    <p>File Size</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"### 📊 Data Preview")
        st.caption(f"Showing first 25 rows of {len(df)} total records")
        st.dataframe(df.head(25), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ Import to Database", use_container_width=True, type="primary", key="import_btn"):
                with st.spinner("Importing data..."):
                    engine = get_engine()
                    result = ingest_export(engine, df)
                st.markdown(f"""
                    <div class="success-message">
                        <h3>✅ Import Complete!</h3>
                        <p style="font-size: 1.1em; margin: 10px 0;"><strong>Batch ID:</strong> {result['export_batch_id']}</p>
                        <p style="font-size: 1.1em; margin: 10px 0;"><strong>New Records:</strong> {result['inserted']}</p>
                        <p style="font-size: 1.1em; margin: 10px 0;"><strong>Updated Records:</strong> {result['updated']}</p>
                        <p style="margin-top: 20px; color: #155724;">Data is now available for check-in processing.</p>
                    </div>
                """, unsafe_allow_html=True)
                
    except Exception as e:
        st.markdown(f"""
            <div style="background: #f8d7da; border: 2px solid #dc3545; padding: 20px; border-radius: 10px;">
                <strong>❌ Error Processing File</strong>
                <p>{str(e)}</p>
            </div>
        """, unsafe_allow_html=True)

if uploaded is None:
    st.markdown("---")
    st.markdown("### 💡 Getting Started")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class="info-card">
                <h4>📋 Required Columns</h4>
                <ul>
                    <li>Status</li>
                    <li>Testing Date/Time</li>
                    <li>SETS Number</li>
                    <li>First Name</li>
                    <li>Last Name</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="info-card">
                <h4>⚙️ File Requirements</h4>
                <ul>
                    <li><strong>Format:</strong> CSV or Excel (.xlsx)</li>
                    <li><strong>Test File:</strong> data/sample_onbase_export.csv</li>
                    <li><strong>Frequency:</strong> Daily updates recommended</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
