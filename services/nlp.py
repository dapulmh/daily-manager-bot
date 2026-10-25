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
  add_timesheet   — wants to log/record a timesheet entry for work done
  list_timesheet  — wants to see logged timesheet entries
  clear_timesheet — wants to clear/reset the timesheet log
  add_expenditure    — wants to log/record money spent (an expense)
  list_expenditure   — wants to see logged expenditure entries
  clear_expenditure  — wants to clear/reset the expenditure log
  analyze_expenditure — wants totals/averages/analysis of their spending
  list_notes       — wants to see saved notes/ideas, optionally filtered to one category
  brainstorm_notes — wants AI brainstorming/analysis over saved notes, optionally on a topic
  unknown         — none of the above

JSON schema:
{{
  "intent": "<one of the intents above>",
  "confidence": <0.0-1.0>,
  "data": {{
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
    "remind_at_iso": "<ISO 8601 datetime of the first occurrence>",
    "recurrence": "<daily|weekly|null>",

    // for add_timesheet:
    "description": "<what was worked on>",
    "date_iso": "<ISO 8601 date (YYYY-MM-DD), default today if not specified>",

    // for add_expenditure:
    "description": "<what the money was spent on>",
    "amount": <integer amount in Rupiah, no currency symbol or separators>,
    "date_iso": "<ISO 8601 date (YYYY-MM-DD), default today if not specified>",

    // for analyze_expenditure:
    "question": "<the specific question being asked about spending, e.g. 'why did I overspend on food this month', or null if it's just a generic request for a summary>",

    // for list_notes:
    "category": "<idea|note|task|question|other, or null to show all>",

    // for brainstorm_notes:
    "topic": "<the specific topic/question to brainstorm about, or null for a general overview>"
  }}
}}
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
            # openai/gpt-oss-20b is a reasoning model - it burns completion tokens on chain-of-thought
            # (visible via resp.choices[0].message.reasoning) before writing the JSON content. Too tight
            # a budget here truncates mid-reasoning and leaves content empty on harder inputs (e.g. relative
            # dates like "next Monday"). 800 leaves enough headroom for reasoning + the JSON payload.
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.warning("NLP JSON parse error: %s | raw: %s", e, raw)
        return {"intent": "unknown", "confidence": 0, "data": {}}

    except Exception as e:
        logger.error("Groq API error: %s", e)
        return {"intent": "unknown", "confidence": 0, "data": {}}
