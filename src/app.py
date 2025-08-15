# app.py
import sys
import os
from pathlib import Path
import streamlit as st

# --- Page Config ---
logo_path = Path("src/components/Logo.png").resolve()
st.set_page_config(
    page_title="Resume Parser",
    page_icon=str(logo_path)
)

# --- Path Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Imports ---
from Login.login import login_signup
from Login.dashboard import admin_dashboard, user_dashboard, ats_scoring_ui

# --- Initialize Session State ---
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("username", None)
st.session_state.setdefault("role", None)
st.session_state.setdefault("page", "login")  # NEW

# --- Routing ---
if st.session_state.page == "login":
    login_signup()

elif st.session_state.page == "dashboard":
    # Sidebar info
    st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")

    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.page = "login"
        st.rerun()

    # Role-based dashboards
    if st.session_state.role == "admin":
        admin_dashboard()
    else:
        user_dashboard()
        ats_scoring_ui()
