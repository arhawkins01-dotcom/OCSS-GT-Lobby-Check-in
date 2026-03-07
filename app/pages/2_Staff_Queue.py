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
from services.checkin_service import CheckinStatusError, set_status, reconcile_future_appointments
from services.coc_service import create_coc_form, get_latest_coc_for_appointment
from services.notification_service import resend_checkin_notifications
from services.queue_service import apply_queue_priority, build_queue_metrics
from services.related_party_service import get_related_parties, update_related_party_status
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

engine, cfg = load_engine_cfg()

# Add role selector to sidebar
role_selector_sidebar()

# Add navigation and auto-refresh in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📍 Quick Navigation")
    if st.button("🏠 Home Dashboard", use_container_width=True):
        st.switch_page("main_app.py")
    if st.button("🖥️ Kiosk Check-In", use_container_width=True):
        st.switch_page("pages/1_Kiosk_CheckIn.py")
    
    st.markdown("---")
    st.markdown("### 🔄 Auto-Refresh")
    auto_refresh = st.checkbox("Enable (10s)", value=False, help="Auto-refresh every 10 seconds to see new check-ins")
    refresh_countdown = st.empty()
    
    if auto_refresh:
        import time
        for i in range(10, 0, -1):
            refresh_countdown.info(f"⏱️ Refreshing in {i}s...")
            time.sleep(1)
        st.rerun()

role = get_user_role()
if role not in ["staff","admin"]:
    st.error("Staff/Admin role required (starter role gate).")
    st.stop()

st.set_page_config(page_title="Staff Queue", layout="wide", page_icon="👥")

# Custom CSS
st.markdown("""
    <style>
    .staff-header {
        text-align: center;
        padding: 30px 20px;
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 12px;
        color: white;
        margin-bottom: 30px;
    }
    .staff-header h1 {
        margin: 0;
        font-size: 2.5em;
    }
    .stats-box {
        background: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stats-box h2 {
        color: #11998e;
        margin: 0;
        font-size: 2.5em;
    }
    .stats-box p {
        margin: 5px 0 0 0;
        color: #666;
        font-size: 1em;
    }
    .action-card {
        background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .legend-item {
        display: inline-block;
        padding: 5px 15px;
        margin: 5px;
        border-radius: 5px;
        font-size: 0.9em;
    }
    .legend-scheduled { background: #fff3cd; border: 1px solid #ffc107; }
    .legend-checkedin { background: #d1ecf1; border: 1px solid #17a2b8; }
    .legend-inprocess { background: #cce5ff; border: 1px solid #007bff; }
    .legend-completed { background: #d4edda; border: 1px solid #28a745; }
    .legend-noshow { background: #f8d7da; border: 1px solid #dc3545; }
    .notification-card {
        background: linear-gradient(135deg, #d1ecf1 0%, #b8daff 100%);
        border-left: 5px solid #17a2b8;
        padding: 15px 20px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.5s ease-out;
    }
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    .patient-detail-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin: 10px 0;
    }
    .future-appt-badge {
        display: inline-block;
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 3px 10px;
        border-radius: 5px;
        font-size: 0.85em;
        margin-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="staff-header">
        <h1>👥 Staff Queue Dashboard</h1>
        <p>Real-time appointment management for today</p>
    </div>
""", unsafe_allow_html=True)

today = date.today().strftime("%Y-%m-%d")

q = text("""
SELECT a.appointment_key, a.testing_datetime, a.sets_number, a.last_name, a.first_name,
       a.assigned_to, a.status_from_onbase, a.part_type, a.appointment_type, a.related_cases,
       v.current_status, v.checkin_time, v.in_process_time, v.completed_time, v.no_show_time
FROM gt_appointments a
JOIN gt_visit_status v ON v.appointment_key=a.appointment_key
WHERE substr(a.testing_datetime,1,10)=:day
ORDER BY a.testing_datetime ASC
""")
with engine.begin() as conn:
    rows = conn.execute(q, {"day": today}).mappings().all()
df = pd.DataFrame([dict(r) for r in rows])
if df.empty:
    st.warning("No appointments loaded for today. Admin: Load Export first.")
    st.stop()

mins = int(cfg.get("no_show_rules",{}).get("minutes_after_appt_to_flag", 30))
now = datetime.now()
df = apply_queue_priority(df, grace_minutes=mins)
df["flag"] = df.apply(
    lambda row: "⚠️ No-Show Candidate" if row.get("priority_bucket") == 4 else "",
    axis=1,
)
metrics = build_queue_metrics(df)

# Statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
        <div class="stats-box">
            <h2>{metrics['total']}</h2>
            <p>Total Appointments</p>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="stats-box">
            <h2>{metrics['waiting']}</h2>
            <p>Waiting</p>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="stats-box">
            <h2>{metrics['avg_wait']}</h2>
            <p>Avg Wait (min)</p>
        </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
        <div class="stats-box">
            <h2>{metrics['late_arrivals']}</h2>
            <p>Late Arrivals</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Recent Check-Ins Notification Section
recent_checkins = df[df["current_status"] == "CHECKED_IN"].copy()
if not recent_checkins.empty:
    st.markdown("### 🔔 Recent Check-Ins - Action Required")
    st.info(f"**{len(recent_checkins)} customer(s)** checked in and waiting to be called.")
    
    for idx, row in recent_checkins.iterrows():
        checkin_time_str = row.get('checkin_time', 'Unknown')
        try:
            checkin_time = datetime.fromisoformat(str(checkin_time_str))
            time_ago = (now - checkin_time).total_seconds() / 60
            time_display = f"{int(time_ago)} min ago" if time_ago < 60 else f"{int(time_ago/60)} hr ago"
        except:
            time_display = "Just now"
        
        # Get future appointments for this customer
        future_appts = reconcile_future_appointments(engine, row['appointment_key'])
        future_badge = f"<span class='future-appt-badge'>📅 {len(future_appts)} future appt(s)</span>" if future_appts else ""
        
        appt_label = f"{row.get('appointment_type', '')} ({row.get('part_type', '')})" if row.get('appointment_type') else row.get('part_type', '')
        
        st.markdown(f"""
            <div class="notification-card">
                <strong style="font-size: 1.2em;">✅ {row['first_name']} {row['last_name']}</strong>{future_badge}
                <br>
                <strong>SETS:</strong> {row['sets_number']} | 
                <strong>Type:</strong> {appt_label} | 
                <strong>Appt Time:</strong> {row['testing_datetime'][:16]} | 
                <strong>Assigned:</strong> {row.get('assigned_to', 'N/A')}
                <br>
                <strong>Checked in:</strong> {time_display}
                {f"<br><span style='color: #856404;'>⚠️ Has {len(future_appts)} future appointment(s) - verify correct visit</span>" if future_appts else ""}
            </div>
        """, unsafe_allow_html=True)
        
        if future_appts:
            with st.expander(f"📋 View {len(future_appts)} Future Appointment(s) for {row['first_name']} {row['last_name']}"):
                for f_appt in future_appts:
                    f_label = f"{f_appt.get('appointment_type', '')} ({f_appt.get('part_type', '')})" if f_appt.get('appointment_type') else f_appt.get('part_type', '')
                    st.markdown(f"""
                        <div class="patient-detail-card">
                            <strong>📅 {f_appt['testing_datetime'][:16]}</strong><br>
                            <strong>Type:</strong> {f_label}<br>
                            <strong>Status:</strong> {f_appt['current_status']}<br>
                            <strong>Assigned:</strong> {f_appt.get('assigned_to', 'N/A')}
                        </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")

# Status legend
st.markdown("""
    <div style="text-align: center; margin: 20px 0;">
        <strong>Status Legend:</strong><br>
        <span class="legend-item legend-scheduled">📋 SCHEDULED</span>
        <span class="legend-item legend-checkedin">✅ CHECKED_IN</span>
        <span class="legend-item legend-inprocess">🔄 IN_PROCESS</span>
        <span class="legend-item legend-completed">✔️ COMPLETED</span>
        <span class="legend-item legend-noshow">❌ NO_SHOW</span>
    </div>
""", unsafe_allow_html=True)

st.markdown("### 📊 Today's Appointments")

# Add tabs for different views
tab1, tab2, tab3 = st.tabs(["All Appointments", "Waiting Queue", "Completed"])

with tab1:
    st.dataframe(df[[
        "queue_order", "priority_bucket", "appointment_key", "first_name", "last_name",
        "testing_datetime", "current_status", "wait_minutes", "late_flag", "flag"
    ]], use_container_width=True, hide_index=True, height=400)

with tab2:
    waiting = df[df["current_status"].isin(["SCHEDULED", "CHECKED_IN"])]
    if waiting.empty:
        st.info("✅ No customers waiting")
    else:
        st.dataframe(waiting, use_container_width=True, hide_index=True, height=400)

with tab3:
    completed = df[df["current_status"].isin(["COMPLETED", "NO_SHOW"])]
    if completed.empty:
        st.info("No completed appointments yet")
    else:
        st.dataframe(completed, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.markdown("""
    <div class="action-card">
        <h3>⚡ Quick Actions</h3>
        <p>Select an appointment below to view details and update status</p>
    </div>
""", unsafe_allow_html=True)

selected = st.selectbox("Select Appointment", df["appointment_key"].tolist(), 
                        format_func=lambda x: f"{x} - {df[df['appointment_key']==x].iloc[0]['first_name']} {df[df['appointment_key']==x].iloc[0]['last_name']} ({df[df['appointment_key']==x].iloc[0]['current_status']})")

# Display selected customer details
if selected:
    customer = df[df["appointment_key"] == selected].iloc[0]
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown(f"""
            <div class="patient-detail-card">
                <h4 style="margin-top: 0; color: #11998e;">👤 Customer Information</h4>
                <strong>Name:</strong> {customer['first_name']} {customer['last_name']}<br>
                <strong>SETS Number:</strong> {customer['sets_number']}<br>
                <strong>Part Type:</strong> {customer.get('part_type', 'N/A')}<br>
                <strong>Appointment Type:</strong> {customer.get('appointment_type', 'N/A')}<br>
                <strong>Related Cases:</strong> {customer.get('related_cases', 'N/A')}
            </div>
        """, unsafe_allow_html=True)
    
    with col_info2:
        st.markdown(f"""
            <div class="patient-detail-card">
                <h4 style="margin-top: 0; color: #11998e;">📅 Appointment Details</h4>
                <strong>Scheduled Time:</strong> {customer['testing_datetime'][:16]}<br>
                <strong>Current Status:</strong> <span style="background: #d1ecf1; padding: 3px 8px; border-radius: 5px;">{customer['current_status']}</span><br>
                <strong>Assigned To:</strong> {customer.get('assigned_to', 'N/A')}<br>
                <strong>Check-in Time:</strong> {customer.get('checkin_time', 'Not checked in')[:16] if customer.get('checkin_time') else 'Not checked in'}
            </div>
        """, unsafe_allow_html=True)
    
    # Check for future appointments
    selected_future = reconcile_future_appointments(engine, selected)
    if selected_future:
        st.warning(f"⚠️ **Multiple Cases Alert:** This customer has {len(selected_future)} future appointment(s). See details below.")
        with st.expander(f"📋 View {len(selected_future)} Future Appointment(s)"):
            for f_appt in selected_future:
                f_label = f"{f_appt.get('appointment_type', '')} ({f_appt.get('part_type', '')})" if f_appt.get('appointment_type') else f_appt.get('part_type', '')
                st.markdown(f"""
                    <div class="patient-detail-card">
                        <strong>📅 {f_appt['testing_datetime'][:16]}</strong><br>
                        <strong>Type:</strong> {f_label}<br>
                        <strong>Status:</strong> {f_appt['current_status']}<br>
                        <strong>Case:</strong> {f_appt.get('related_cases', 'N/A')}
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("#### Related Parties")
    related_parties = get_related_parties(engine, selected)
    if not related_parties:
        st.caption("No related parties found for this appointment group.")
    else:
        st.caption("Staff-only view: track attendance, identity verification, and COC inclusion for linked parties.")
        for party in related_parties:
            party_key = party["appointment_key"]
            label = f"{party.get('party_name', 'Unknown')} ({party.get('part_type', 'Unknown Role')})"
            if party.get("is_anchor"):
                label += " - Primary Check-In"

            cols = st.columns([3, 2, 2, 2, 1])
            with cols[0]:
                st.write(label)
            with cols[1]:
                arrival = st.selectbox(
                    f"Arrival {party_key}",
                    ["UNKNOWN", "PRESENT", "ABSENT", "CHECKED_IN_SEPARATELY", "NOT_REQUIRED"],
                    index=["UNKNOWN", "PRESENT", "ABSENT", "CHECKED_IN_SEPARATELY", "NOT_REQUIRED"].index(
                        str(party.get("arrival_status", "UNKNOWN")).upper()
                    ) if str(party.get("arrival_status", "UNKNOWN")).upper() in ["UNKNOWN", "PRESENT", "ABSENT", "CHECKED_IN_SEPARATELY", "NOT_REQUIRED"] else 0,
                    key=f"arrival_{selected}_{party_key}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                idv = st.checkbox(
                    "ID Verified",
                    value=bool(party.get("identity_verified_flag", 0)),
                    key=f"idv_{selected}_{party_key}",
                )
            with cols[3]:
                coc_in = st.checkbox(
                    "Include on COC",
                    value=bool(party.get("coc_included_flag", 1)),
                    key=f"cocinc_{selected}_{party_key}",
                )
            with cols[4]:
                if st.button("Save", key=f"save_rel_{selected}_{party_key}"):
                    update_related_party_status(
                        engine=engine,
                        appointment_key=selected,
                        related_appointment_key=party_key,
                        arrival_status=arrival,
                        identity_verified_flag=idv,
                        coc_included_flag=coc_in,
                        updated_by=role.upper(),
                    )
                    st.success(f"Saved related party status for {party.get('party_name', 'party')}.")
                    st.rerun()

    st.markdown("#### Chain Of Custody (COC)")
    latest_coc = get_latest_coc_for_appointment(engine, selected)
    if latest_coc:
        st.info(
            f"Latest COC: {latest_coc.get('coc_id','')[:8]}... | Status: {latest_coc.get('status','DRAFT')} | Generated: {latest_coc.get('generated_at') or latest_coc.get('created_at')}"
        )
    else:
        st.caption("No COC has been generated yet for this appointment.")

    c_coc1, c_coc2 = st.columns(2)
    with c_coc1:
        if st.button("📄 Generate COC", use_container_width=True, key="gen_coc_selected"):
            coc = create_coc_form(
                engine=engine,
                appointment_key=selected,
                collector_name=role.upper(),
                notes="Generated from staff queue.",
                generated_by=role.upper(),
            )
            if coc.get("success"):
                st.success(f"COC generated: {coc.get('coc_id','')[:8]}...")
                st.rerun()
            else:
                st.error(coc.get("error", "Unable to generate COC."))
    with c_coc2:
        if st.button("🔁 Re-Generate COC", use_container_width=True, key="regen_coc_selected"):
            coc = create_coc_form(
                engine=engine,
                appointment_key=selected,
                collector_name=role.upper(),
                notes="Re-generated from staff queue.",
                generated_by=role.upper(),
            )
            if coc.get("success"):
                st.success(f"New COC generated: {coc.get('coc_id','')[:8]}...")
                st.rerun()
            else:
                st.error(coc.get("error", "Unable to re-generate COC."))
    
    st.markdown("#### Update Status")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("✅ Assisted Check-In", use_container_width=True, type="secondary", disabled=(customer['current_status'] != "SCHEDULED")):
            try:
                set_status(engine, selected, "CHECKED_IN", performed_by="STAFF", notes="Assisted check-in")
                st.rerun()
            except CheckinStatusError as exc:
                st.error(str(exc))
        if customer['current_status'] != "SCHEDULED":
            st.caption("Already checked in")
    with c2:
        if st.button("🔄 Start (In Process)", use_container_width=True, type="primary", disabled=(customer['current_status'] not in ["CHECKED_IN", "SCHEDULED"])):
            try:
                set_status(engine, selected, "IN_PROCESS", performed_by="STAFF")
                st.rerun()
            except CheckinStatusError as exc:
                st.error(str(exc))
        if customer['current_status'] not in ["CHECKED_IN", "SCHEDULED"]:
            st.caption("Not ready")
    with c3:
        if st.button("✔️ Complete", use_container_width=True, type="primary", disabled=(customer['current_status'] != "IN_PROCESS")):
            try:
                set_status(engine, selected, "COMPLETED", performed_by="STAFF")
                st.rerun()
            except CheckinStatusError as exc:
                st.error(str(exc))
        if customer['current_status'] != "IN_PROCESS":
            st.caption("Must be in process")
    with c4:
        if role=="admin":
            if st.button("❌ Mark No Show", use_container_width=True, disabled=(customer['current_status'] != "SCHEDULED")):
                try:
                    set_status(engine, selected, "NO_SHOW", performed_by="ADMIN")
                    st.rerun()
                except CheckinStatusError as exc:
                    st.error(str(exc))
            if customer['current_status'] != "SCHEDULED":
                st.caption("Only scheduled")
        else:
            st.caption("⚠️ Admin only")

    st.markdown("#### Notifications")
    if st.button("📨 Re-Send Check-In Notifications", use_container_width=True, key="resend_notifs"):
        result = resend_checkin_notifications(engine, selected, performed_by=role.upper())
        st.success(f"Notification resend complete. SMS: {result.get('sms',{}).get('status')} | Email: {result.get('email',{}).get('status')}")

# Auto-refresh toggle
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("💡 **Tip:** This page shows real-time check-ins. Refresh to see latest updates.")
with col2:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
