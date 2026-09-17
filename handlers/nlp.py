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
import services.timesheet as timesheet_svc
import services.expenditure as expenditure_svc
import services.insight as insight_svc
from utils.formatter import (
    format_daily, format_events, format_cards, format_reminders, format_timesheet,
    format_expenditure, format_expenditure_insight, format_rupiah, escape
)

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
    try:
        await _route_intent(update, intent, data, text)
    except Exception as e:
        logger.error("handle_message routing error (intent=%s): %s", intent, e)
        await update.message.reply_text(f"❌ Error: {escape(str(e))}", parse_mode=ParseMode.MARKDOWN_V2)


async def _route_intent(update: Update, intent: str, data: dict, text: str):
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
            title         = data.get("title", text),
            remind_at_iso = data["remind_at_iso"],
            recurrence    = data.get("recurrence"),
        )
        from utils.dt import fmt_dt
        time_str   = escape(fmt_dt(rem["remind_at_iso"]))
        title      = escape(rem["title"])
        recurrence = rem.get("recurrence")
        rec_label  = escape(f" · repeats {recurrence}") if recurrence else ""
        await update.message.reply_text(
            f"⏰ Reminder set: *{title}* at `{time_str}`{rec_label}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "list_reminders":
        rems = reminder_svc.list_reminders()
        await update.message.reply_text(
            format_reminders(rems), parse_mode=ParseMode.MARKDOWN_V2
        )

    elif intent == "add_timesheet":
        entry = timesheet_svc.add_entry(
            description = data.get("description", text),
            date_iso    = data.get("date_iso"),
        )
        await update.message.reply_text(
            f"📝 Logged for `{escape(entry['date_iso'])}`: {escape(entry['description'])}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "list_timesheet":
        entries = timesheet_svc.list_entries()
        await update.message.reply_text(
            format_timesheet(entries), parse_mode=ParseMode.MARKDOWN_V2
        )

    elif intent == "clear_timesheet":
        n = timesheet_svc.clear_entries()
        await update.message.reply_text(f"🗑 Cleared {n} timesheet entr{'y' if n == 1 else 'ies'}\\.")

    elif intent == "add_expenditure":
        try:
            amount = int(round(float(data.get("amount"))))
        except (TypeError, ValueError):
            await update.message.reply_text(
                "I need an amount\\. Try: _'spent 25000 on lunch'_",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        entry = expenditure_svc.add_entry(
            description = data.get("description", text),
            amount      = amount,
            date_iso    = data.get("date_iso"),
        )
        await update.message.reply_text(
            f"💸 Logged for `{escape(entry['date_iso'])}`: {escape(entry['description'])} — "
            f"{escape(format_rupiah(entry['amount']))}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif intent == "list_expenditure":
        entries = expenditure_svc.list_entries()
        await update.message.reply_text(
            format_expenditure(entries), parse_mode=ParseMode.MARKDOWN_V2
        )

    elif intent == "clear_expenditure":
        n = expenditure_svc.clear_entries()
        await update.message.reply_text(f"🗑 Cleared {n} expenditure entr{'y' if n == 1 else 'ies'}\\.")

    elif intent == "analyze_expenditure":
        result, insight_text = insight_svc.analyze_with_insight(question=data.get("question"))
        await update.message.reply_text(
            format_expenditure_insight(result, insight_text), parse_mode=ParseMode.MARKDOWN_V2
        )

    else:
        await update.message.reply_text(
            "🤔 Not sure what you mean\\. Type /start to see available commands\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
