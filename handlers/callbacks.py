"""
handlers/callbacks.py
Handles InlineKeyboardButton presses (priority picker, confirm dialogs).
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

import services.trello as trello

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    # Format: "priority:<card_id>:<priority>"
    if data.startswith("priority:"):
        _, card_id, priority = data.split(":", 2)
        try:
            trello.set_card_priority(card_id, priority)
            await query.edit_message_text(
                f"✅ Priority set to *{priority}* for card `{card_id}`",
                parse_mode="MarkdownV2",
            )
        except Exception as e:
            logger.error("priority callback error: %s", e)
            await query.edit_message_text(f"❌ Failed: {e}")

    # Format: "move:<card_id>:<list_name>"
    elif data.startswith("move:"):
        _, card_id, list_name = data.split(":", 2)
        try:
            trello.move_card(card_id, list_name)
            await query.edit_message_text(
                f"✅ Card moved to *{list_name}*",
                parse_mode="MarkdownV2",
            )
        except Exception as e:
            logger.error("move callback error: %s", e)
            await query.edit_message_text(f"❌ Failed: {e}")

    else:
        await query.edit_message_text("Unknown action.")
