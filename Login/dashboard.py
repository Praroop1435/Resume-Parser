import streamlit as st
import requests
import os
import re

# CONFIG
API_BASE = "http://localhost:8000"  # Backend FastAPI URL
JD_FOLDER = "JDs"

# HELPERS
def _pretty_label(filename: str) -> str:
    """Convert raw filename into a clean label for dropdowns."""
    name = filename.rsplit(".", 1)[0]
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\b(job\s*description|jd)\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()

# USER DASHBOARD 
def user_dashboard():
    st.title("🙋 Resume Parser & ATS Scoring")

    # 1. Load job descriptions
    if not os.path.exists(JD_FOLDER):
        st.error("⚠️ JD folder not found!")
        return

    all_jds = [f for f in os.listdir(JD_FOLDER) if f.lower().endswith(".txt")]

    if not all_jds:
        st.error("⚠️ No Job Descriptions found in the 'JDs' folder.")
        return

    # Pretty labels
    label_to_file = {_pretty_label(fn): fn for fn in sorted(all_jds)}
    labels = list(label_to_file.keys())

    # 2. Search JD
    search_query = st.text_input("🔍 Search Job Description")
    if search_query:
        labels = [lbl for lbl in labels if search_query.lower() in lbl.lower()]

    if not labels:
        st.warning("No matching Job Descriptions found.")
        return

    # 3. Select JD
    selected_label = st.selectbox("📂 Select a Job Description", labels, index=0)
    selected_jd = label_to_file[selected_label]

    # 4. Upload resume
    uploaded_file = st.file_uploader("📄 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    # 5. Fresher or Non-Fresher
    fresher_choice = st.radio("👤 Candidate Type", ["Fresher", "Experienced"], index=0)
    fresher = True if fresher_choice == "Fresher" else False

    # 6. Analyze Resume
    if uploaded_file and st.button("🚀 Analyze Resume"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            data = {"jd_file": selected_jd, "fresher": str(fresher)}  # backend expects form values as str

            resp = requests.post(f"{API_BASE}/analyze_resume", files=files, data=data)

            if resp.status_code != 200:
                st.error(f"❌ ATS API Error: {resp.status_code}")
                return

            result = resp.json()

            # Tabs for Preview & ATS Scoring
            tab1, tab2 = st.tabs(["📄 Resume Preview", "📊 ATS Scoring"])

            # ----- TAB 1: Preview -----
            with tab1:
                preview = result.get("preview", {})
                st.subheader("Resume Summary")
                st.write(f"**Name:** {preview.get('name', 'N/A')}")
                st.write(f"**Email:** {preview.get('email', 'N/A')}")

            # ----- TAB 2: ATS Score -----
            with tab2:
                st.subheader("ATS Score")

                final_score = result.get("final_score", 0)

                st.markdown(f"### 🎯 Your ATS Score is **{final_score}**")

                # Optional: Give simple interpretation
                if final_score >= 80:
                    st.success("✅ Strong Match – Your resume aligns very well with the job description!")
                elif final_score >= 60:
                    st.info("⚖️ Moderate Match – Your resume is good, but can be improved.")
                else:
                    st.warning("❌ Weak Match – Consider adding missing skills and tailoring your resume.")


        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")

# ---------------- ADMIN DASHBOARD ---------------- #
def admin_dashboard():
    st.title("👑 Admin Dashboard")
    st.write("Manage users, job descriptions, and logs.")

    tabs = st.tabs(["👥 Users", "📂 Job Descriptions", "📊 Logs"])

    # Users Tab
    with tabs[0]:
        st.subheader("Registered Users")
        users = [
            {"username": "admin", "role": "admin"},
            {"username": "user1", "role": "user"},
        ]
        for u in users:
            st.write(f"**{u['username']}** ({u['role']})")

        new_user = st.text_input("Add new user")
        if st.button("Create User"):
            st.success(f"User {new_user} added!")

    # Job Descriptions Tab
    with tabs[1]:
        st.subheader("Manage Job Descriptions")
        jds = [f for f in os.listdir(JD_FOLDER) if f.endswith(".txt")]
        st.write(jds)

        uploaded_jd = st.file_uploader("Upload new JD", type=["txt"])
        if uploaded_jd:
            save_path = os.path.join(JD_FOLDER, uploaded_jd.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_jd.read())
            st.success("New JD uploaded!")

    # Logs Tab
    with tabs[2]:
        st.subheader("Activity Logs")
        logs = [
            {"user": "user1", "jd": "Data Scientist.txt", "score": 78},
            {"user": "user2", "jd": "ML Engineer.txt", "score": 85},
        ]
        for log in logs:
            st.write(f"{log['user']} → {log['jd']} → Score: {log['score']}%")
