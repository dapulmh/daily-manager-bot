"""
utils/auth.py
Simple decorator that rejects any user who isn't you.
"""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from utils.config import CONFIG


def private_only(func):
    """Reject messages from anyone other than ALLOWED_USER_ID."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != CONFIG["ALLOWED_USER_ID"]:
            await update.message.reply_text("⛔ Not authorised.")
            return
        return await func(update, ctx, *args, **kwargs)
    return wrapper
