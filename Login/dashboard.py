import streamlit as st
import requests

# Backend API endpoint for ingestion
BACKEND_URL = "http://localhost:8000/ingest"  # Change when deployed

def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, view logs, and more here.")
    # Add admin features here (e.g., user list, logs, etc.)

def user_dashboard():
    st.title("🙋 User Dashboard - Resume Parser")
    st.write("Upload your resume below.")

    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        if st.button("Submit Resume"):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                response = requests.post(BACKEND_URL, files=files)

                if response.status_code == 200:
                    st.success("✅ Resume uploaded and processed successfully!")
                else:
                    st.error(f"❌ Upload failed! Server returned status {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
