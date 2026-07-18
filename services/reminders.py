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
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from utils.config import CONFIG
from utils.dt import TZ

logger = logging.getLogger(__name__)

# Use /data volume on Fly.io if it exists, otherwise fall back to local
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(".")
STORE_FILE = _DATA_DIR / "reminders.json"
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
    fire_dt = datetime.fromisoformat(rem["remind_at_iso"])
    if fire_dt.tzinfo is None:
        fire_dt = TZ.localize(fire_dt)

    recurrence = rem.get("recurrence")
    kwargs = {"reminder_id": rem["id"], "title": rem["title"], "recurrence": recurrence}

    if recurrence == "daily":
        trigger = CronTrigger(hour=fire_dt.hour, minute=fire_dt.minute, timezone=TZ)
    elif recurrence == "weekly":
        # day_of_week: 0=Monday … 6=Sunday, matches Python's weekday()
        trigger = CronTrigger(
            day_of_week=fire_dt.weekday(),
            hour=fire_dt.hour,
            minute=fire_dt.minute,
            timezone=TZ,
        )
    else:
        if fire_dt < datetime.now(TZ):
            return  # already past, skip one-time reminders
        trigger = "date"
        _scheduler.add_job(
            _fire_reminder,
            trigger=trigger,
            run_date=fire_dt,
            kwargs=kwargs,
            id=rem["id"],
            replace_existing=True,
            misfire_grace_time=120,
        )
        return

    _scheduler.add_job(
        _fire_reminder,
        trigger=trigger,
        kwargs=kwargs,
        id=rem["id"],
        replace_existing=True,
        misfire_grace_time=120,
    )


async def _fire_reminder(reminder_id: str, title: str, recurrence: str = None) -> None:
    label = {"daily": " (daily)", "weekly": " (weekly)"}.get(recurrence, "")
    await _bot.send_message(
        chat_id=CONFIG["ALLOWED_USER_ID"],
        text=f"⏰ *Reminder{label}:* {title}",
        parse_mode="Markdown",
    )
    # Only remove one-time reminders; recurring ones stay in the store
    if not recurrence:
        reminders = [r for r in _load() if r["id"] != reminder_id]
        _save(reminders)


# ── Public API ───────────────────────────────────────────────────────────────

def add_reminder(title: str, remind_at_iso: str, recurrence: str = None) -> dict:
    """Add and persist a reminder. recurrence: 'daily' | 'weekly' | None."""
    rem = {
        "id":            str(uuid.uuid4()),
        "title":         title,
        "remind_at_iso": remind_at_iso,
        "recurrence":    recurrence,
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
