"""
services/google_calendar.py
Wraps the Google Calendar API.
Auth uses OAuth2 with local token.json caching (first run opens a browser).
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from utils.config import CONFIG
from utils.dt import today_range, week_range, TZ
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    creds = None
    token_file = CONFIG["GOOGLE_TOKEN_FILE"]
    creds_file  = CONFIG["GOOGLE_CREDENTIALS_FILE"]

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_events(time_range: str = "today") -> list[dict]:
    """Return events for 'today' or 'week'."""
    service = _get_service()
    start, end = today_range() if time_range == "today" else week_range()

    result = service.events().list(
        calendarId=CONFIG["GOOGLE_CALENDAR_ID"],
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
        maxResults=20,
    ).execute()

    return result.get("items", [])


def create_event(summary: str, start_iso: str, end_iso: str,
                 description: str = "", reminder_minutes: int = None) -> dict:
    """Create a calendar event. Returns the created event dict."""
    service = _get_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": CONFIG["TIMEZONE"]},
        "end":   {"dateTime": end_iso,   "timeZone": CONFIG["TIMEZONE"]},
    }

    if reminder_minutes is not None:
        event["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": reminder_minutes}],
        }

    return service.events().insert(
        calendarId=CONFIG["GOOGLE_CALENDAR_ID"],
        body=event,
    ).execute()


def delete_event(event_id: str) -> None:
    service = _get_service()
    service.events().delete(
        calendarId=CONFIG["GOOGLE_CALENDAR_ID"],
        eventId=event_id,
    ).execute()
