#!/usr/bin/env python3
"""
One-time LinkedIn OAuth 2.0 setup.

Usage:
    python scripts/linkedin_auth.py

Steps it handles automatically:
  1. Opens your browser to LinkedIn authorisation URL
  2. Starts a local callback server on http://localhost:8765
  3. Exchanges the code for an access token
  4. Writes the token to  .linkedin_token.json  (in project root)
  5. Copies LINKEDIN_ACCESS_TOKEN line into .env

Required .env vars BEFORE running:
    LINKEDIN_CLIENT_ID=your_client_id
    LINKEDIN_CLIENT_SECRET=your_client_secret
    LINKEDIN_ORG_ID=your_org_numeric_id
"""

import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8765/callback"
TOKEN_FILE    = ROOT / ".linkedin_token.json"
ENV_FILE      = ROOT / ".env"

SCOPES = [
    "r_organization_social",   # page + post analytics
    "rw_organization_admin",   # needed by Community Management API
    "openid",
    "profile",
]


# ── Callback server ───────────────────────────────────────────────────

_received_code  = None
_received_state = None
_received_error = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        global _received_code, _received_state, _received_error
        qs = parse_qs(urlparse(self.path).query)
        _received_code  = qs.get("code",  [None])[0]
        _received_state = qs.get("state", [None])[0]
        _received_error = qs.get("error", [None])[0]

        if _received_code:
            body = b"<h2>Authorised! You can close this tab.</h2>"
        else:
            body = f"<h2>Error: {_received_error}</h2>".encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):   # silence request log
        pass


# ── Main flow ─────────────────────────────────────────────────────────

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌  LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set in .env")
        print("   Add them first, then re-run this script.")
        sys.exit(1)

    state = secrets.token_urlsafe(16)

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode({
            "response_type": "code",
            "client_id":     CLIENT_ID,
            "redirect_uri":  REDIRECT_URI,
            "scope":         " ".join(SCOPES),
            "state":         state,
        })
    )

    print("🔑  Opening LinkedIn authorisation in your browser …")
    print(f"    URL: {auth_url}\n")
    webbrowser.open(auth_url)

    # Start local callback server
    server = HTTPServer(("localhost", 8765), _Handler)
    server.timeout = 120  # 2-minute window

    print("⏳  Waiting for LinkedIn redirect on http://localhost:8765/callback …")
    while _received_code is None and _received_error is None:
        server.handle_request()

    if _received_error:
        print(f"❌  LinkedIn returned error: {_received_error}")
        sys.exit(1)

    if _received_state != state:
        print("❌  State mismatch — possible CSRF. Aborting.")
        sys.exit(1)

    print("✅  Received authorisation code. Exchanging for access token …")

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          _received_code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()

    expires_in = token_data.get("expires_in", 5184000)   # default 60 days
    token_data["expires_at"] = int(time.time()) + expires_in

    # Save token file
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"💾  Token saved to {TOKEN_FILE}")

    # Update .env
    set_key(str(ENV_FILE), "LINKEDIN_ACCESS_TOKEN", token_data["access_token"])
    print(f"📝  LINKEDIN_ACCESS_TOKEN updated in {ENV_FILE}")

    expires_days = expires_in // 86400
    print(
        f"\n🎉  Done! Token is valid for ~{expires_days} days.\n"
        f"    Re-run this script before it expires to stay connected."
    )


if __name__ == "__main__":
    main()
