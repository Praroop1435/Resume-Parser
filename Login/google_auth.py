# Login/google_auth.py
import os
from dotenv import load_dotenv
from streamlit_oauth import OAuth2Component

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
AUTHORIZE_URL = os.getenv("AUTHORIZE_URL", "https://accounts.google.com/o/oauth2/v2/auth")
TOKEN_URL = os.getenv("TOKEN_URL", "https://oauth2.googleapis.com/token")
REFRESH_TOKEN_URL = os.getenv("REFRESH_TOKEN_URL", TOKEN_URL)
REVOKE_TOKEN_URL = os.getenv("REVOKE_TOKEN_URL", "")

REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501/callback/google")
SCOPE = os.getenv("SCOPE", "openid email profile")  # keep as a plain string

# Create component with full endpoints (matches the README API)
oauth2 = OAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    AUTHORIZE_URL,
    TOKEN_URL,
    REFRESH_TOKEN_URL,
    REVOKE_TOKEN_URL
)
