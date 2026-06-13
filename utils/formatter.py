"""
utils/formatter.py
Builds nicely formatted Telegram messages (MarkdownV2-safe).
"""

from utils.dt import fmt_dt, fmt_date


def escape(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


# ── Calendar ─────────────────────────────────────────────────────────────────

def format_events(events: list[dict], header: str) -> str:
    if not events:
        return f"*{escape(header)}*\n\n_Nothing scheduled_ 🎉"

    lines = [f"*{escape(header)}*\n"]
    for ev in events:
        start = ev.get("start", {})
        time_str = fmt_dt(start.get("dateTime") or start.get("date", ""))
        title    = escape(ev.get("summary", "Untitled"))
        lines.append(f"🗓 `{time_str}` — {title}")

    return "\n".join(lines)


# ── Trello ────────────────────────────────────────────────────────────────────

_PRIORITY_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "🟢"}


def _card_priority_emoji(card: dict) -> str:
    for lbl in card.get("labels", []):
        emoji = _PRIORITY_EMOJI.get(lbl.get("color", ""))
        if emoji:
            return emoji
    return "⚪"


def format_cards(cards: list[dict], header: str) -> str:
    if not cards:
        return f"*{escape(header)}*\n\n_No tasks_ ✅"

    lines = [f"*{escape(header)}*\n"]
    for card in cards:
        emoji = _card_priority_emoji(card)
        title = escape(card.get("name", "Untitled"))
        due   = card.get("due")
        due_str = f" \\(due {escape(fmt_date(due))}\\)" if due else ""
        lines.append(f"{emoji} {title}{due_str}")

    return "\n".join(lines)


# ── Reminders ────────────────────────────────────────────────────────────────

def format_reminders(reminders: list[dict]) -> str:
    if not reminders:
        return "*Reminders*\n\n_None set_ ✅"

    lines = ["*Reminders*\n"]
    for rem in reminders:
        time_str = escape(fmt_dt(rem["remind_at_iso"]))
        title    = escape(rem["title"])
        lines.append(f"⏰ `{time_str}` — {title}")

    return "\n".join(lines)


# ── Combined daily digest ─────────────────────────────────────────────────────

def format_daily(events: list[dict], cards: list[dict]) -> str:
    cal_part  = format_events(events, "Today's calendar")
    task_part = format_cards(cards,   "Open tasks")
    return f"{cal_part}\n\n{task_part}"
