"""
services/nlp.py
Uses Groq (free Llama 3) to parse natural language into structured intents.
Falls back gracefully if Groq is unavailable.
"""

import json
import logging
from groq import Groq
from utils.config import CONFIG
from utils.dt import now

logger = logging.getLogger(__name__)
_client = Groq(api_key=CONFIG["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are a JSON-only intent parser for a personal productivity bot.
The user's local time is: {local_time}
The user's timezone is: {timezone}

Analyse the user's message and return ONLY a valid JSON object — no markdown, no explanation.

Possible intents:
  view_today      — wants to see today's schedule/tasks
  view_week       — wants to see this week's overview
  add_event       — wants to add a calendar event
  add_task        — wants to add a Trello card/task
  set_reminder    — wants a reminder for an existing or new item
  list_reminders  — wants to see current reminders
  unknown         — none of the above

JSON schema:
{
  "intent": "<one of the intents above>",
  "confidence": <0.0-1.0>,
  "data": {
    // for add_event:
    "title": "<event title>",
    "start_iso": "<ISO 8601 datetime in user's timezone>",
    "end_iso":   "<ISO 8601 datetime, default +1h if not specified>",
    "reminder_minutes": <int or null>,

    // for add_task:
    "title": "<task title>",
    "priority": "<high|medium|low|null>",
    "due_iso": "<ISO 8601 date or null>",
    "list_name": "<Trello list name or null>",

    // for set_reminder:
    "title": "<what to remind>",
    "remind_at_iso": "<ISO 8601 datetime>"
  }
}
If a field is not mentioned, set it to null. Always output valid JSON.
"""


def parse_intent(text: str) -> dict:
    """
    Parse user text into a structured intent dict.
    Returns {"intent": "unknown", "confidence": 0, "data": {}} on failure.
    """
    local_time = now().strftime("%Y-%m-%d %H:%M %Z")
    prompt = SYSTEM_PROMPT.format(
        local_time=local_time,
        timezone=CONFIG["TIMEZONE"],
    )

    try:
        resp = _client.chat.completions.create(
            model=CONFIG["GROQ_MODEL"],
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": text},
            ],
            temperature=0,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.warning("NLP JSON parse error: %s | raw: %s", e, raw)
        return {"intent": "unknown", "confidence": 0, "data": {}}

    except Exception as e:
        logger.error("Groq API error: %s", e)
        return {"intent": "unknown", "confidence": 0, "data": {}}
