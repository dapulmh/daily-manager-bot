"""
Daily Manager Bot — entry point
Starts the Telegram bot with polling.
"""

import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from handlers.commands import (
    start, today, week, add_event, add_task, reminders
)
from handlers.nlp import handle_message
from handlers.callbacks import handle_callback
from utils.config import CONFIG

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    app = ApplicationBuilder().token(CONFIG["TELEGRAM_TOKEN"]).build()

    # Slash commands
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("today",    today))
    app.add_handler(CommandHandler("week",     week))
    app.add_handler(CommandHandler("add",      add_event))   # /add Meeting at 3pm tomorrow
    app.add_handler(CommandHandler("task",     add_task))    # /task Buy groceries #high
    app.add_handler(CommandHandler("remind",   reminders))   # /remind list | clear

    # Inline button callbacks (priority picker, confirm dialogs, etc.)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Natural language fallback — anything that isn't a command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
