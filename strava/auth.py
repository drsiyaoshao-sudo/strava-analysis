"""auth.py — Strava OAuth 2.0 token management."""
from __future__ import annotations
import http.server
import threading
import webbrowser
import urllib.parse
import requests
import json
import os
import sys
import time
from datetime import datetime

CLIENT_ID     = "214027"
CLIENT_SECRET = "5ca14f76d588f9ffff253bf4990c6d8d842d1938"
REDIRECT_URI  = "http://localhost:8080/callback"
TOKEN_FILE    = "strava_token.json"

_auth_code: str | None = None


class _OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Auth complete. Close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


def get_token() -> str:
    global _auth_code

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = json.load(f)
        if token.get("expires_at", 0) > datetime.now().timestamp() + 60:
            print("Using cached Strava token.")
            return token["access_token"]
        print("Refreshing token...")
        r = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": token["refresh_token"],
        })
        token = r.json()
        with open(TOKEN_FILE, "w") as f:
            json.dump(token, f)
        return token["access_token"]

    server = http.server.HTTPServer(("localhost", 8080), _OAuthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = (f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
           f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=read,activity:read_all")
    print("Opening Strava in your browser...")
    webbrowser.open(url)
    print("Waiting for authorization", end="", flush=True)
    while _auth_code is None:
        time.sleep(0.5)
        print(".", end="", flush=True)
    print(" done.")
    server.shutdown()
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "code": _auth_code, "grant_type": "authorization_code",
    })
    token = r.json()
    if "access_token" not in token:
        print("Auth failed:", token)
        sys.exit(1)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)
    return token["access_token"]
