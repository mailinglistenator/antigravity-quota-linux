"""OAuth and account management."""
import json
import os
import time
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

from config import (
    ACCOUNTS_FILE,
    CLIENT_ID,
    CLIENT_SECRET,
    OAUTH_SCOPES,
    OAUTH_AUTH_URL,
    OAUTH_TOKEN_URL,
    REDIRECT_PORT,
    REDIRECT_URI,
)

def load_accounts():
    if not ACCOUNTS_FILE.exists():
        return []
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_accounts(accounts):
    temp_file = ACCOUNTS_FILE.with_suffix(".tmp")
    with open(temp_file, "w") as f:
        json.dump(accounts, f, indent=2)
    os.chmod(temp_file, 0o600)
    temp_file.replace(ACCOUNTS_FILE)

def refresh_access_token(refresh_token):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(OAUTH_TOKEN_URL, data=data, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to refresh access token ({resp.status_code}): {resp.text}")
    token_data = resp.json()
    return token_data.get("access_token"), token_data.get("expires_in", 3600)

def fetch_user_profile(access_token):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return {}

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/oauth-callback":
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                OAuthCallbackHandler.auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = """
                <html>
                <body style="font-family: -apple-system, sans-serif; background: #0d1117; color: #f0f6fc; text-align: center; padding-top: 80px;">
                    <div style="display: inline-block; background: #161b22; border: 1px solid #30363d; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);">
                        <h2 style="color: #2ea043; margin-top: 0;">✓ Google Account Connected!</h2>
                        <p style="color: #8b949e;">Your Antigravity account has been added to the Quota Monitor.</p>
                        <p style="font-size: 14px; color: #58a6ff;">You can close this tab and return to the app window.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
                return
        self.send_response(400)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_interactive_oauth(name=None):
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent select_account",
    }
    login_url = f"{OAUTH_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    server = HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
    OAuthCallbackHandler.auth_code = None

    try:
        webbrowser.open(login_url)
    except Exception:
        pass

    server.timeout = 120
    start_time = time.time()
    while OAuthCallbackHandler.auth_code is None and (time.time() - start_time < 120):
        server.handle_request()

    if not OAuthCallbackHandler.auth_code:
        raise TimeoutError("Authorization timed out or was cancelled.")

    code = OAuthCallbackHandler.auth_code

    exchange_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    resp = requests.post(OAUTH_TOKEN_URL, data=exchange_data, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to exchange authorization code: {resp.text}")

    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if not refresh_token:
        raise ValueError("Google did not return a refresh token.")

    profile = fetch_user_profile(access_token)
    email = profile.get("email", "unknown@gmail.com")
    # Default name directly to the Gmail address if not explicitly specified
    acc_name = name if name and name.strip() else email

    account_entry = {
        "name": acc_name,
        "email": email,
        "type": "oauth",
        "refresh_token": refresh_token,
        "added_at": int(time.time()),
    }

    accounts = load_accounts()
    existing = next((i for i, a in enumerate(accounts) if a.get("email") == email), None)
    if existing is not None:
        accounts[existing] = account_entry
    else:
        accounts.append(account_entry)

    save_accounts(accounts)
    return account_entry

def add_active_local_account(name=None):
    accounts = load_accounts()
    # Check if local session already exists
    for acc in accounts:
        if acc.get("type") == "local_active":
            return acc

    default_email = "primary_account"
    acc_name = name if name and name.strip() else default_email

    account_entry = {
        "name": acc_name,
        "email": default_email,
        "type": "local_active",
        "added_at": int(time.time()),
    }
    accounts.insert(0, account_entry)
    save_accounts(accounts)
    return account_entry

def rename_account(identifier, new_name):
    identifier = identifier.lower().strip()
    new_name = new_name.strip()
    if not new_name:
        return False
    accounts = load_accounts()
    for a in accounts:
        if a.get("name", "").lower() == identifier or a.get("email", "").lower() == identifier:
            a["name"] = new_name
            save_accounts(accounts)
            return True
    return False

def remove_account(identifier):
    identifier = identifier.lower()
    accounts = load_accounts()
    new_accounts = [
        a for a in accounts
        if a.get("name", "").lower() != identifier and a.get("email", "").lower() != identifier
    ]
    if len(new_accounts) != len(accounts):
        save_accounts(new_accounts)
        return True
    return False
