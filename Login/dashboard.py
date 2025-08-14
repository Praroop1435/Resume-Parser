import streamlit as st
import requests
import os

# Backend API endpoint for ingestion
BACKEND_URL = "http://localhost:8000/ingest"  # Change when deployed

def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, view logs, and more here.")
    # Add admin features here (e.g., user list, logs, etc.)

def user_dashboard():
    st.title("🙋 User Dashboard - Resume Parser")
    st.write("Choose a Job Description and upload your resume for ATS scoring.")

    jd_folder = "JDs"
    all_jds = [f for f in os.listdir(jd_folder) if f.endswith(".txt")]

    # Step 2: Search JDs
    search_query = st.text_input("Search Job Description", "")
    filtered_jds = [jd for jd in all_jds if search_query.lower() in jd.lower()]

    # Step 3: Select JD
    selected_jd = st.selectbox("Select a Job Description", filtered_jds)
 
    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    # Step 4: Submit
    if uploaded_file and st.button("Submit Resume"):
        try:
            files = {
                "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
            }
            data = {"jd_file": selected_jd}  # Send JD filename to backend

            response = requests.post(BACKEND_URL, files=files, data=data)

            if response.status_code == 200:
                st.success("✅ Resume uploaded and processed successfully!")
                st.write(response.json())  # Show ATS score or result
            else:
                st.error(f"❌ Upload failed! Server returned status {response.status_code}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
