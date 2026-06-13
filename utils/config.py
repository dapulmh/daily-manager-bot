"""
utils/config.py
Loads all credentials and settings from environment variables / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val

CONFIG = {
    # Telegram
    "TELEGRAM_TOKEN":       _require("TELEGRAM_TOKEN"),
    "ALLOWED_USER_ID":      int(_require("ALLOWED_USER_ID")),  # your Telegram numeric user ID

    # Google Calendar (OAuth2 — file paths)
    "GOOGLE_CREDENTIALS_FILE": os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
    "GOOGLE_TOKEN_FILE":       os.getenv("GOOGLE_TOKEN_FILE",       "token.json"),
    "GOOGLE_CALENDAR_ID":      os.getenv("GOOGLE_CALENDAR_ID",      "primary"),

    # Trello
    "TRELLO_API_KEY":   _require("TRELLO_API_KEY"),
    "TRELLO_TOKEN":     _require("TRELLO_TOKEN"),
    "TRELLO_BOARD_ID":  _require("TRELLO_BOARD_ID"),

    # Groq (free NLP)
    "GROQ_API_KEY":     _require("GROQ_API_KEY"),
    "GROQ_MODEL":       os.getenv("GROQ_MODEL", "llama3-8b-8192"),

    # Timezone
    "TIMEZONE": os.getenv("TIMEZONE", "Asia/Jakarta"),
}
