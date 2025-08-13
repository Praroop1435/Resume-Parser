import streamlit as st
import time
from Login.auth import create_user, verify_user
from main import db_name, admin_user, admin_pass

def login_signup():
    st.title("Resume Parser App")

    tab1, tab2 = st.tabs(["🔐 Sign in", "📝 Sign Up"])

    # --- LOGIN TAB ---
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            valid, role = verify_user(username, password)
            if valid:
                # Store session state
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role

                # Redirect to dashboard
                st.title("Logging in...")
                time.sleep(1)
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid username or password")

    # --- SIGNUP TAB ---
    with tab2:
        new_user = st.text_input("New Username", key="signup_user")
        new_pass = st.text_input("New Password", type="password", key="signup_pass")
        role = "user"  # Default role for signup

        if st.button("Sign Up"):
            if create_user(new_user, new_pass, role):
                st.success("Account created! You can log in now.")
            else:
                st.error("Username already exists!")
