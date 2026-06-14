"""
handlers/commands.py
All /command handlers.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import private_only
from utils.formatter import format_daily, format_events, format_cards, format_reminders, escape
import services.google_calendar as gcal
import services.trello as trello
import services.reminders as reminder_svc
from services.nlp import parse_intent

logger = logging.getLogger(__name__)


@private_only
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Daily Manager Bot*\n\n"
        "Commands:\n"
        "/today — today's calendar \\+ tasks\n"
        "/week — this week's calendar\n"
        "/add \\<event\\> — add a calendar event\n"
        "/task \\<task\\> — create a Trello card\n"
        "/remind — list or clear reminders\n\n"
        "Or just type naturally — I'll figure it out\\!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


@private_only
async def today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching your day…", parse_mode=ParseMode.MARKDOWN_V2)
    try:
        events = gcal.get_events("today")
        cards  = trello.get_cards()
        msg    = format_daily(events, cards)
    except Exception as e:
        logger.error("today error: %s", e)
        msg = f"❌ Error fetching data: {escape(str(e))}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


@private_only
async def week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching your week…", parse_mode=ParseMode.MARKDOWN_V2)
    try:
        events = gcal.get_events("week")
        msg    = format_events(events, "This week")
    except Exception as e:
        logger.error("week error: %s", e)
        msg = f"❌ Error: {escape(str(e))}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


@private_only
async def add_event(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /add Meeting with Ali at 3pm tomorrow
    Passes the full text to NLP to extract title + times.
    """
    raw = " ".join(ctx.args)
    if not raw:
        await update.message.reply_text(
            "Usage: `/add <event description>`\nExample: `/add Dentist at 2pm tomorrow`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await update.message.reply_text("Parsing…", parse_mode=ParseMode.MARKDOWN_V2)
    parsed = parse_intent(f"Add calendar event: {raw}")
    data   = parsed.get("data", {})

    if not data.get("start_iso"):
        await update.message.reply_text(
            "Couldn't figure out the time\\. Try: `/add Meeting at 3pm tomorrow`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        ev = gcal.create_event(
            summary         = data.get("title", raw),
            start_iso       = data["start_iso"],
            end_iso         = data["end_iso"] or data["start_iso"],
            reminder_minutes= data.get("reminder_minutes"),
        )
        title = ev.get("summary", "Event")
        link  = ev.get("htmlLink", "")
        await update.message.reply_text(
            f"✅ Added *{title}*\n[Open in Google Calendar]({link})",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("add_event error: %s", e)
        await update.message.reply_text(f"❌ Failed to create event: {e}")


@private_only
async def add_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /task Buy groceries #high
    Supports optional #high / #medium / #low priority tag.
    """
    raw = " ".join(ctx.args)
    if not raw:
        await update.message.reply_text(
            "Usage: `/task <title> [\\#high|\\#medium|\\#low]`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Quick priority extraction from hashtag
    priority = None
    title    = raw
    for p in ("high", "medium", "low"):
        tag = f"#{p}"
        if tag in raw.lower():
            priority = p
            title = raw.lower().replace(tag, "").strip()
            break

    # If no hashtag, use NLP
    if not priority:
        parsed   = parse_intent(f"Create task: {raw}")
        priority = parsed.get("data", {}).get("priority")

    try:
        card = trello.create_card(name=title, priority=priority)
        p_str = f" \\[{priority}\\]" if priority else ""
        await update.message.reply_text(
            f"✅ Task created{p_str}: *{title}*\n[Open in Trello]({card.get('url','')})",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("add_task error: %s", e)
        await update.message.reply_text(f"❌ Failed: {e}")


@private_only
async def reminders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /remind           — show reminders
    /remind clear     — clear all reminders
    """
    arg = ctx.args[0].lower() if ctx.args else ""

    if arg == "clear":
        n = reminder_svc.clear_all_reminders()
        await update.message.reply_text(f"🗑 Cleared {n} reminder(s)\\.")
        return

    rems = reminder_svc.list_reminders()
    from utils.formatter import format_reminders
    await update.message.reply_text(
        format_reminders(rems),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
