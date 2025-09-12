# Login/login.py
import streamlit as st
import httpx
from Login.google_auth import oauth2, REDIRECT_URI, SCOPE

USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

def google_login():
    # Show a centered login card
    st.markdown(
        """
        <style>
        .login-card {
            max-width: 400px;
            margin: 80px auto;
            padding: 30px;
            border-radius: 12px;
            background-color: #ffffff;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .login-title {
            font-size: 28px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 20px;
        }
        .login-subtitle {
            font-size: 16px;
            color: #666666;
            margin-bottom: 30px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Resume Parser App</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sign in to continue</div>', unsafe_allow_html=True)

        # Google login button
        result = oauth2.authorize_button(
            "🔐 Login with Google",
            REDIRECT_URI,
            SCOPE,
            key="google_login"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        return result


def login_signup():
    result = google_login()
    if result:
        # Save login state
        st.session_state.logged_in = True
        st.session_state.user_info = result
        st.session_state.page = "dashboard"
        st.rerun()