from __future__ import annotations
import streamlit as st

def role_selector_sidebar() -> None:
    st.sidebar.markdown("### Role (starter repo)")
    st.sidebar.selectbox("Select role", ["kiosk","staff","admin"], key="role")

def get_user_role() -> str:
    return st.session_state.get("role","kiosk")
