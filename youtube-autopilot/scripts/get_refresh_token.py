"""Jalankan SEKALI di komputer kamu untuk mendapatkan refresh token YouTube.

Langkah: simpan file OAuth dari Google Cloud sebagai client_secret.json di folder ini,
lalu jalankan:  python scripts/get_refresh_token.py
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

with open(path, encoding="utf-8") as f:
    info = json.load(f)
info = info.get("installed") or info.get("web")

print("\n=== Simpan 3 nilai ini sebagai GitHub Secrets (jangan dibagikan ke siapa pun) ===")
print("YT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
