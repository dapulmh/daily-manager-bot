"""
handlers/commands.py
All /command handlers.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import private_only
from utils.formatter import (
    format_daily, format_events, format_cards, format_reminders, format_timesheet,
    format_expenditure, format_expenditure_insight, format_rupiah, escape,
    format_notes, format_notes_insight
)
import services.google_calendar as gcal
import services.trello as trello
import services.reminders as reminder_svc
import services.timesheet as timesheet_svc
import services.expenditure as expenditure_svc
import services.insight as insight_svc
import services.notes as notes_svc
import services.notes_insight as notes_insight_svc
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
        "/remind — list or clear reminders\n"
        "/timesheet \\<description\\> — log a timesheet entry \\(no args to view, `clear` to reset\\)\n"
        "/expense \\<description\\> \\<amount\\> — log an expenditure \\(no args to view, `clear` to reset\\)\n"
        "/analysis \\[question\\] — expenditure stats \\+ AI insight \\(ask it something, e\\.g\\. `how can I save more?`\\)\n"
        "/note \\[text\\] — save a note/idea \\(auto\\-classified; no args to view, `clear` to reset\\)\n"
        "/brainstorm \\[topic\\] — AI brainstorming over your saved notes\n\n"
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


@private_only
async def timesheet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /timesheet                — show logged entries
    /timesheet clear          — clear all entries
    /timesheet <description>  — log an entry for today
    """
    raw = " ".join(ctx.args)
    arg = raw.lower()

    if arg == "clear":
        n = timesheet_svc.clear_entries()
        await update.message.reply_text(f"🗑 Cleared {n} timesheet entr{'y' if n == 1 else 'ies'}\\.")
        return

    if not raw:
        entries = timesheet_svc.list_entries()
        await update.message.reply_text(
            format_timesheet(entries),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    entry = timesheet_svc.add_entry(description=raw)
    await update.message.reply_text(
        f"📝 Logged for `{escape(entry['date_iso'])}`: {escape(entry['description'])}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@private_only
async def expense(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /expense                          — show logged entries
    /expense clear                    — clear all entries
    /expense <description> <amount>   — log an expenditure entry for today
    """
    raw = " ".join(ctx.args)
    arg = raw.lower()

    if arg == "clear":
        n = expenditure_svc.clear_entries()
        await update.message.reply_text(f"🗑 Cleared {n} expenditure entr{'y' if n == 1 else 'ies'}\\.")
        return

    if not raw:
        entries = expenditure_svc.list_entries()
        await update.message.reply_text(
            format_expenditure(entries),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    description, _, amount_str = raw.rpartition(" ")
    if not description or not amount_str.isdigit():
        await update.message.reply_text(
            "Usage: `/expense <description> <amount>`\nExample: `/expense Lunch at warung 25000`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    entry = expenditure_svc.add_entry(description=description, amount=int(amount_str))
    await update.message.reply_text(
        f"💸 Logged for `{escape(entry['date_iso'])}`: {escape(entry['description'])} — "
        f"{escape(format_rupiah(entry['amount']))}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@private_only
async def analysis(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /analysis            — expenditure stats + AI-generated insight
    /analysis <question> — ask a specific question about your spending
    """
    question = " ".join(ctx.args) if ctx.args else None
    await update.message.reply_text("Crunching your numbers…", parse_mode=ParseMode.MARKDOWN_V2)
    try:
        result, insight_text = insight_svc.analyze_with_insight(question=question)
        msg = format_expenditure_insight(result, insight_text)
    except Exception as e:
        logger.error("analysis error: %s", e)
        msg = f"❌ Error generating analysis: {escape(str(e))}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


@private_only
async def note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /note              — show saved notes, grouped by category
    /note clear        — clear all notes
    /note <text>       — save a note; classified into a category immediately
    """
    raw = " ".join(ctx.args)
    arg = raw.lower()

    if arg == "clear":
        n = notes_svc.clear_entries()
        await update.message.reply_text(f"🗑 Cleared {n} note{'s' if n != 1 else ''}\\.")
        return

    if not raw:
        entries = notes_svc.list_entries()
        await update.message.reply_text(
            format_notes(entries),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await update.message.reply_text("Classifying…", parse_mode=ParseMode.MARKDOWN_V2)
    entry = notes_insight_svc.add_note(raw)
    await update.message.reply_text(
        f"🗒 Saved as *{escape(entry['category'])}*: {escape(entry['text'])}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@private_only
async def brainstorm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /brainstorm          — general AI brainstorming overview of saved notes
    /brainstorm <topic>  — brainstorm specifically about a topic/question
    """
    topic = " ".join(ctx.args) if ctx.args else None
    await update.message.reply_text("Thinking it through…", parse_mode=ParseMode.MARKDOWN_V2)
    try:
        result, insight_text = notes_insight_svc.analyze_notes(topic=topic)
        msg = format_notes_insight(result, insight_text)
    except Exception as e:
        logger.error("brainstorm error: %s", e)
        msg = f"❌ Error generating brainstorm: {escape(str(e))}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
