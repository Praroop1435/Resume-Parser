# dashboard.py
import streamlit as st

def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, view logs, and more here.")
    # Add admin features here (e.g., user list, logs, etc.)

def user_dashboard():
    st.title("🙋 User Dashboard - Resume Parser")
    st.write("Upload your resume below.")
    st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])
