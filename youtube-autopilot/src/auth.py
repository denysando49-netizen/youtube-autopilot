"""Autentikasi ke YouTube lewat refresh token yang disimpan di GitHub Secrets."""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def credentials():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def youtube(creds):
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def analytics(creds):
    return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
