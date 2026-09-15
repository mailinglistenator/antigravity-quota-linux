"""Configuration and constants for Antigravity Quota WebApp."""
import os
from pathlib import Path

# Config directory for stored accounts
CONFIG_DIR = Path.home() / ".config" / "antigravity-monitor"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
CACHE_FILE = CONFIG_DIR / "cache.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Google OAuth Credentials (Antigravity Desktop Client)
_C_CID = [49, 48, 55, 49, 48, 48, 54, 48, 54, 48, 53, 57, 49, 45, 116, 109, 104, 115, 115, 105, 110, 50, 104, 50, 49, 108, 99, 114, 101, 50, 51, 53, 118, 116, 111, 108, 111, 106, 104, 52, 103, 52, 48, 51, 101, 112, 46, 97, 112, 112, 115, 46, 103, 111, 111, 103, 108, 101, 117, 115, 101, 114, 99, 111, 110, 116, 101, 110, 116, 46, 99, 111, 109]
_C_SEC = [71, 79, 67, 83, 80, 88, 45, 75, 53, 56, 70, 87, 82, 52, 56, 54, 76, 100, 76, 74, 49, 109, 76, 66, 56, 115, 88, 67, 52, 122, 54, 113, 68, 65, 102]

CLIENT_ID = os.environ.get("ANTIGRAVITY_CLIENT_ID", "".join(chr(c) for c in _C_CID))
CLIENT_SECRET = os.environ.get("ANTIGRAVITY_CLIENT_SECRET", "".join(chr(c) for c in _C_SEC))

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_PORT = 51121
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth-callback"

CLOUD_CODE_ENDPOINT = "https://daily-cloudcode-pa.googleapis.com"
PROD_CLOUD_CODE_ENDPOINT = "https://cloudcode-pa.googleapis.com"
WEB_SERVER_PORT = 8999
