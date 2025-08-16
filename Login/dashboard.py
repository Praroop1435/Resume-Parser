import streamlit as st
import requests
import os
import re

API_BASE = "http://localhost:8000"  # centralize base url

def _pretty_label(filename: str) -> str:
    """Convert raw filename into clean label for dropdowns."""
    name = filename.rsplit(".", 1)[0]
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\b(job\s*description|jd)\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()

def user_dashboard():
    st.title("🙋 Resume Parser & ATS Scoring")

    # Load job descriptions
    jd_folder = "JDs"
    all_jds = [f for f in os.listdir(jd_folder) if f.lower().endswith(".txt")]

    if not all_jds:
        st.error("⚠️ No Job Descriptions found in the 'JDs' folder.")
        return

    # Map: Pretty label ↔ Filename
    label_to_file = {_pretty_label(fn): fn for fn in sorted(all_jds)}
    labels = list(label_to_file.keys())

    # Search bar
    search_query = st.text_input("🔍 Search Job Description")
    if search_query:
        labels = [lbl for lbl in labels if search_query.lower() in lbl.lower()]

    if not labels:
        st.warning("No matching Job Descriptions found.")
        return

    # Select JD
    selected_label = st.selectbox("📂 Select a Job Description", labels, index=0)
    selected_jd = label_to_file[selected_label]

    # Upload resume
    uploaded_file = st.file_uploader("📄 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file and st.button("🚀 Analyze Resume"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            data = {"jd_file": selected_jd}

            response = requests.post(f"{API_BASE}/analyze_resume", files=files, data=data)

            if response.status_code == 200:
                result = response.json()

                # Tabs for Preview & Score
                tab1, tab2 = st.tabs(["📄 Resume Preview", "📊 ATS Scoring"])

                with tab1:
                    preview = result.get("preview", {})
                    st.subheader("Resume Summary")
                    st.write(f"**Name:** {preview.get('name', 'N/A')}")
                    st.write(f"**Email:** {preview.get('email', 'N/A')}")

                    skills = preview.get("skills_top", [])
                    if skills:
                        st.write("**Top Skills:** " + ", ".join(skills))

                with tab2:
                    st.subheader("ATS Score")
                    st.metric("Match Score", f"{result.get('score', 0)}%")

                    missing = result.get("missing_keywords", [])
                    if missing:
                        st.write("❌ Missing Keywords:")
                        st.write(", ".join(missing))
                    else:
                        st.success("All important keywords are covered!")

            else:
                st.error(f"❌ Server Error: {response.status_code}")
        except Exception as e:
            st.error(f"Error: {str(e)}")


def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, view logs, and more here.")

    tabs = st.tabs(["👥 Users", "📂 Job Descriptions", "📊 Logs"])

    # Users Tab
    with tabs[0]:
        st.subheader("Registered Users")
        # In real app, pull from DB
        users = [
            {"username": "admin", "role": "admin"},
            {"username": "user1", "role": "user"}
        ]
        for u in users:
            st.write(f"**{u['username']}** ({u['role']})")

        new_user = st.text_input("Add new user")
        if st.button("Create User"):
            st.success(f"User {new_user} added!")

    # Job Descriptions Tab
    with tabs[1]:
        st.subheader("Manage Job Descriptions")
        jd_folder = "JDs"
        jds = [f for f in os.listdir(jd_folder) if f.endswith(".txt")]
        st.write(jds)

        uploaded_jd = st.file_uploader("Upload new JD", type=["txt"])
        if uploaded_jd:
            save_path = os.path.join(jd_folder, uploaded_jd.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_jd.read())
            st.success("New JD uploaded!")

    # Logs Tab
    with tabs[2]:
        st.subheader("Activity Logs")
        # Example logs (replace with DB fetch)
        logs = [
            {"user": "user1", "jd": "Data Scientist.txt", "score": 78},
            {"user": "user2", "jd": "ML Engineer.txt", "score": 85},
        ]
        for log in logs:
            st.write(f"{log['user']} → {log['jd']} → Score: {log['score']}%")
