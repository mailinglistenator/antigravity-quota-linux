"""Quota fetching engine for Antigravity accounts."""
import datetime
import json
import re
import subprocess
import time
import urllib3
import requests

from auth_manager import refresh_access_token, load_accounts
from config import CLOUD_CODE_ENDPOINT, PROD_CLOUD_CODE_ENDPOINT

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_time_delta(iso_reset_time):
    if not iso_reset_time:
        return "N/A"
    try:
        iso_str = iso_reset_time.replace("Z", "+00:00")
        target_time = datetime.datetime.fromisoformat(iso_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = target_time - now
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            return "Ready"

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes}m")
        if not parts:
            parts.append(f"{seconds}s")
        return "in " + " ".join(parts)
    except Exception:
        return iso_reset_time

def find_active_language_server():
    try:
        ps_out = subprocess.check_output(["ps", "-eo", "pid,args"], text=True)
        csrf_token = None
        server_pid = None

        for line in ps_out.splitlines():
            if "language_server" in line and "--csrf_token" in line:
                m = re.search(r"--csrf_token[=\s]+([a-zA-Z0-9_\-]+)", line)
                if m:
                    csrf_token = m.group(1)
                    server_pid = line.strip().split()[0]
                    break

        if not csrf_token or not server_pid:
            return None, None

        ports = []
        try:
            ss_out = subprocess.check_output(["ss", "-tulpn"], text=True, stderr=subprocess.DEVNULL)
            for s_line in ss_out.splitlines():
                if f"pid={server_pid}," in s_line:
                    port_match = re.search(r"127\.0\.0\.1:(\d+)", s_line)
                    if port_match:
                        ports.append(int(port_match.group(1)))
        except Exception:
            pass

        for port in ports:
            try:
                resp = requests.post(
                    f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus",
                    headers={
                        "Content-Type": "application/json",
                        "x-codeium-csrf-token": csrf_token,
                    },
                    json={},
                    verify=False,
                    timeout=1.5,
                )
                if resp.status_code == 200:
                    return port, csrf_token
            except Exception:
                continue

        return None, None
    except Exception:
        return None, None

def extract_quota_summary_data(summary_json, user_status_json=None):
    result = {
        "gemini": {
            "5h_remaining": 100.0,
            "5h_reset": "Ready",
            "weekly_remaining": 100.0,
            "weekly_reset": "Ready",
        },
        "claude_gpt": {
            "5h_remaining": 100.0,
            "5h_reset": "Ready",
            "weekly_remaining": 100.0,
            "weekly_reset": "Ready",
        },
        "plan": "Google AI Pro",
    }

    if user_status_json:
        user_tier = user_status_json.get("userTier", {})
        result["plan"] = user_tier.get("name") or user_tier.get("id") or "Active Plan"

    groups = summary_json.get("response", {}).get("groups", [])
    if not groups and "groups" in summary_json:
        groups = summary_json.get("groups", [])

    for group in groups:
        d_name = group.get("displayName", "").lower()
        target = None
        if "gemini" in d_name:
            target = result["gemini"]
        elif "claude" in d_name or "gpt" in d_name or "3p" in d_name:
            target = result["claude_gpt"]

        if not target:
            continue

        for bucket in group.get("buckets", []):
            window = bucket.get("window", "")
            fraction = bucket.get("remainingFraction", 1.0)
            pct = round(fraction * 100, 1)
            reset_str = parse_time_delta(bucket.get("resetTime"))

            if window == "5h":
                target["5h_remaining"] = pct
                target["5h_reset"] = reset_str
            elif window == "weekly":
                target["weekly_remaining"] = pct
                target["weekly_reset"] = reset_str

    return result

def fetch_local_active_quota():
    port, csrf_token = find_active_language_server()
    if not port or not csrf_token:
        return {
            "status": "offline",
            "error": "Antigravity 2.0 language server not running.",
        }

    headers = {
        "Content-Type": "application/json",
        "x-codeium-csrf-token": csrf_token,
    }

    try:
        q_resp = requests.post(
            f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary",
            headers=headers,
            json={},
            verify=False,
            timeout=5,
        )
        if q_resp.status_code != 200:
            return {"status": "error", "error": f"Language server HTTP {q_resp.status_code}"}

        q_json = q_resp.json()

        u_resp = requests.post(
            f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus",
            headers=headers,
            json={},
            verify=False,
            timeout=5,
        )
        u_json = u_resp.json() if u_resp.status_code == 200 else {}

        parsed = extract_quota_summary_data(q_json, u_json)
        parsed["status"] = "online"
        parsed["last_updated"] = int(time.time())
        return parsed
    except Exception as e:
        return {"status": "error", "error": str(e)}

def fetch_oauth_account_quota(account):
    refresh_token = account.get("refresh_token")
    if not refresh_token:
        return {"status": "error", "error": "No refresh token."}

    try:
        access_token, _ = refresh_access_token(refresh_token)
    except Exception as e:
        return {"status": "error", "error": f"Token refresh failed: {e}"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/2.12.2 (Linux x86_64)",
    }

    endpoints = [CLOUD_CODE_ENDPOINT, PROD_CLOUD_CODE_ENDPOINT]
    last_err = None

    for ep in endpoints:
        url = f"{ep}/v1internal:retrieveUserQuotaSummary"
        try:
            resp = requests.post(url, headers=headers, json={}, timeout=8)
            if resp.status_code == 200:
                parsed = extract_quota_summary_data(resp.json())
                parsed["status"] = "online"
                parsed["last_updated"] = int(time.time())
                return parsed
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = str(e)

    return {"status": "error", "error": last_err or "Failed to query quota"}

def fetch_all_accounts_quota():
    accounts = load_accounts()
    if not accounts:
        return []

    results = []
    for acc in accounts:
        acc_type = acc.get("type", "oauth")
        name = acc.get("name", "Account")
        email = acc.get("email", "")

        if acc_type == "local_active":
            data = fetch_local_active_quota()
        else:
            data = fetch_oauth_account_quota(acc)

        data["name"] = name
        data["email"] = email
        data["type"] = acc_type
        results.append(data)

    return results
