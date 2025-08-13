# app.py
import sys
import os
from pathlib import Path
import streamlit as st

logo_path = Path("src/components/Logo.png").resolve()

st.set_page_config(
    page_title="Resume Parser",
    page_icon=str(logo_path)
)


# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Login.login import login_signup
import streamlit as st
from Login.dashboard import admin_dashboard, user_dashboard

# Initialize session state keys
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

# Route based on login status
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()  # Refresh the app

    # Role-based dashboard
    if st.session_state.role == "admin":
        admin_dashboard()
    else:
        user_dashboard()
else:
    login_signup()




