import streamlit as st
import requests
import os
import re

# Backend API endpoint for preprocessing
BACKEND_URL = "http://localhost:8000/preprocess"  # Change when deployed

def _pretty_label(filename: str) -> str:
    """Convert a raw filename into a clean display label."""
    name = filename.rsplit(".", 1)[0]
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\b(job\s*description|jd)\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()

def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, view logs, and more here.")
    # Admin features go here (e.g., user list, logs, etc.)

def user_dashboard():
    st.title("🙋 User Dashboard — Resume Parser")
    st.write("Select a Job Description and upload your resume for ATS scoring.")

    # Load JD list
    jd_folder = "JDs"
    all_jds = [f for f in os.listdir(jd_folder) if f.lower().endswith(".txt")]

    if not all_jds:
        st.error("No Job Descriptions found in the 'JDs' folder.")
        return

    # Map: Pretty label ↔ Filename
    label_to_file = {_pretty_label(fn): fn for fn in sorted(all_jds)}
    labels = list(label_to_file.keys())

    # Search filter
    search_query = st.text_input("Search Job Description")
    if search_query:
        labels = [lbl for lbl in labels if search_query.lower() in lbl.lower()]

    if not labels:
        st.warning("No matching Job Descriptions found.")
        return

    # Dropdown
    selected_label = st.selectbox("Select a Job Description", labels, index=0)
    selected_jd = label_to_file[selected_label]

    # Resume upload
    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    # Submit button
    if uploaded_file and st.button("Submit Resume"):
        try:
            files = {
                "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
            }
            data = {"jd_file": selected_jd}

            response = requests.post(BACKEND_URL, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                st.success("✅ Resume uploaded and processed successfully!")

                if "preview" in result:
                    preview = result["preview"]

                    st.subheader("📄 Resume Summary")
                    st.write(f"**Name:** {preview.get('name', 'N/A')}")
                    st.write(f"**Email:** {preview.get('email', 'N/A')}")

                    skills = preview.get("skills_top", [])
                    if skills:
                        st.write("**Top Skills:**")
                        st.write(", ".join(skills))
                else:
                    st.info("Resume processed but no preview data available.")
            else:
                st.error(f"❌ Upload failed! Server returned {response.status_code}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def ats_scoring_ui():
    st.header("ATS Resume Scoring")

    resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    jd_text = st.text_area("Paste Job Description")

    if st.button("Calculate ATS Score"):
        if resume_file and jd_text:
            files = {"resume": resume_file}
            data = {"jd": jd_text}

            # Call backend API
            response = requests.post("http://localhost:8000/calculate_ats", files=files, data=data)

            if response.status_code == 200:
                st.success(f"ATS Score: {response.json()['score']}%")
                st.write("Missing Keywords:", response.json()["missing_keywords"])
            else:
                st.error("Error calculating ATS score. Please try again.")
        else:
            st.warning("Please upload a resume and enter JD text.")
