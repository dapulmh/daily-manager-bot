"""
services/reminders.py
Lightweight reminder system using APScheduler + a local JSON store.
Reminders survive bot restarts by persisting to reminders.json.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from utils.config import CONFIG
from utils.dt import TZ

logger = logging.getLogger(__name__)

STORE_FILE = Path("reminders.json")
_scheduler: AsyncIOScheduler = None
_bot: Bot = None


# ── Persistence ──────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return []


def _save(reminders: list[dict]) -> None:
    STORE_FILE.write_text(json.dumps(reminders, indent=2))


# ── Scheduler lifecycle ──────────────────────────────────────────────────────

def init_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _scheduler, _bot
    _bot = bot
    _scheduler = AsyncIOScheduler(timezone=TZ)
    _scheduler.start()

    # Re-schedule any saved reminders
    for rem in _load():
        _schedule_job(rem)

    logger.info("Reminder scheduler started, %d reminder(s) loaded", len(_load()))
    return _scheduler


def _schedule_job(rem: dict) -> None:
    """Add a one-off job to the scheduler."""
    fire_dt = datetime.fromisoformat(rem["remind_at_iso"])
    if fire_dt.tzinfo is None:
        fire_dt = TZ.localize(fire_dt)

    if fire_dt < datetime.now(TZ):
        return  # already past

    _scheduler.add_job(
        _fire_reminder,
        trigger="date",
        run_date=fire_dt,
        kwargs={"reminder_id": rem["id"], "title": rem["title"]},
        id=rem["id"],
        replace_existing=True,
        misfire_grace_time=120,
    )


async def _fire_reminder(reminder_id: str, title: str) -> None:
    await _bot.send_message(
        chat_id=CONFIG["ALLOWED_USER_ID"],
        text=f"⏰ *Reminder:* {title}",
        parse_mode="Markdown",
    )
    # Remove from store
    reminders = [r for r in _load() if r["id"] != reminder_id]
    _save(reminders)


# ── Public API ───────────────────────────────────────────────────────────────

def add_reminder(title: str, remind_at_iso: str) -> dict:
    """Add and persist a reminder. Returns the stored reminder dict."""
    rem = {
        "id":           str(uuid.uuid4()),
        "title":        title,
        "remind_at_iso": remind_at_iso,
    }
    reminders = _load()
    reminders.append(rem)
    _save(reminders)
    _schedule_job(rem)
    return rem


def list_reminders() -> list[dict]:
    return _load()


def clear_all_reminders() -> int:
    reminders = _load()
    count = len(reminders)
    for rem in reminders:
        try:
            _scheduler.remove_job(rem["id"])
        except Exception:
            pass
    _save([])
    return count
