"""
handlers/nlp.py
Handles free-text messages — parses intent and routes to the right action.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import private_only
from services.nlp import parse_intent
import services.google_calendar as gcal
import services.trello as trello
import services.reminders as reminder_svc
from utils.formatter import format_daily, format_events, format_cards, format_reminders

logger = logging.getLogger(__name__)


@private_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    # Show typing indicator
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    parsed     = parse_intent(text)
    intent     = parsed.get("intent", "unknown")
    confidence = parsed.get("confidence", 0)
    data       = parsed.get("data", {})

    logger.info("NLP → intent=%s conf=%.2f data=%s", intent, confidence, data)

    # Low-confidence fallback
    if confidence < 0.6 and intent != "view_today":
        await update.message.reply_text(
            "🤔 I'm not sure what you mean\\. Try:\n"
            "• `/today` — your schedule\n"
            "• `/add Meeting at 3pm` — add event\n"
            "• `/task Buy milk \\#high` — add task",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # ── Route by intent ───────────────────────────────────────────────────────

    if intent == "view_today":
        await update.message.reply_text("Fetching your day…")
        events = gcal.get_events("today")
        cards  = trello.get_cards()
        await update.message.reply_text(
            format_daily(events, cards), parse_mode=ParseMode.MARKDOWN_V2
        )

    elif intent == "view_week":
        await update.message.reply_text("Fetching your week…")
        events = gcal.get_events("week")
        await update.message.reply_text(
            format_events(events, "This week"), parse_mode=ParseMode.MARKDOWN_V2
        )

    elif intent == "add_event":
        if not data.get("start_iso"):
            await update.message.reply_text(
                "I need a time\\. Try: _'add standup at 9am tomorrow'_",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        ev = gcal.create_event(
            summary          = data.get("title", text),
            start_iso        = data["start_iso"],
            end_iso          = data.get("end_iso") or data["start_iso"],
            reminder_minutes = data.get("reminder_minutes"),
        )
        title = ev.get("summary", "Event")
        link  = ev.get("htmlLink", "")
        await update.message.reply_text(
            f"✅ Added *{title}*\n[Open in Google Calendar]({link})",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "add_task":
        card = trello.create_card(
            name      = data.get("title", text),
            priority  = data.get("priority"),
            due       = data.get("due_iso"),
            list_name = data.get("list_name"),
        )
        p_str = f" \\[{data['priority']}\\]" if data.get("priority") else ""
        await update.message.reply_text(
            f"✅ Task created{p_str}: *{card.get('name','')}*\n"
            f"[Open in Trello]({card.get('url','')})",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "set_reminder":
        if not data.get("remind_at_iso"):
            await update.message.reply_text(
                "When should I remind you? Try: _'remind me about X at 5pm'_",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        rem = reminder_svc.add_reminder(
            title        = data.get("title", text),
            remind_at_iso= data["remind_at_iso"],
        )
        from utils.dt import fmt_dt
        from utils.formatter import escape
        time_str = escape(fmt_dt(rem["remind_at_iso"]))
        title    = escape(rem["title"])
        await update.message.reply_text(
            f"⏰ Reminder set: *{title}* at `{time_str}`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "list_reminders":
        rems = reminder_svc.list_reminders()
        await update.message.reply_text(
            format_reminders(rems), parse_mode=ParseMode.MARKDOWN_V2
        )

    else:
        await update.message.reply_text(
            "🤔 Not sure what you mean\\. Type /start to see available commands\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
