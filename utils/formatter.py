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

_RECURRENCE_LABEL = {"daily": " 🔁 daily", "weekly": " 🔁 weekly"}


def format_reminders(reminders: list[dict]) -> str:
    if not reminders:
        return "*Reminders*\n\n_None set_ ✅"

    lines = ["*Reminders*\n"]
    for rem in reminders:
        time_str  = escape(fmt_dt(rem["remind_at_iso"]))
        title     = escape(rem["title"])
        rec_label = escape(_RECURRENCE_LABEL.get(rem.get("recurrence", ""), ""))
        lines.append(f"⏰ `{time_str}` — {title}{rec_label}")

    return "\n".join(lines)


# ── Timesheet ────────────────────────────────────────────────────────────────

def format_timesheet(entries: list[dict]) -> str:
    if not entries:
        return "*Timesheet*\n\n_No entries logged_ 📝"

    by_date: dict[str, list[str]] = {}
    for entry in entries:
        by_date.setdefault(entry["date_iso"], []).append(entry["description"])

    lines = ["*Timesheet*\n"]
    for date_iso in sorted(by_date):
        lines.append(f"🗓 *{escape(date_iso)}*")
        for desc in by_date[date_iso]:
            lines.append(f"  • {escape(desc)}")

    return "\n".join(lines)


# ── Expenditure ──────────────────────────────────────────────────────────────

def format_rupiah(amount: int) -> str:
    return f"Rp {amount:,}".replace(",", ".")


def format_expenditure(entries: list[dict]) -> str:
    if not entries:
        return "*Expenditure*\n\n_No entries logged_ 💸"

    by_date: dict[str, list[dict]] = {}
    for entry in entries:
        by_date.setdefault(entry["date_iso"], []).append(entry)

    lines = ["*Expenditure*\n"]
    for date_iso in sorted(by_date):
        day_total = sum(e["amount"] for e in by_date[date_iso])
        lines.append(f"🗓 *{escape(date_iso)}* — {escape(format_rupiah(day_total))}")
        for e in by_date[date_iso]:
            lines.append(f"  • {escape(e['description'])} — {escape(format_rupiah(e['amount']))}")

    return "\n".join(lines)


def format_expenditure_analysis(analysis: dict) -> str:
    if analysis["entry_count"] == 0:
        return "*Expenditure Analysis*\n\n_No entries logged_ 📊"

    start, end   = analysis["date_range"]
    high_day, high_amt = analysis["highest_day"]
    low_day, low_amt   = analysis["lowest_day"]

    lines = [
        "*Expenditure Analysis*\n",
        f"📅 Range: {escape(start)} → {escape(end)}",
        f"🗓 Days recorded: {analysis['total_days']}",
        f"🧾 Entries: {analysis['entry_count']}",
        f"💰 Total: {escape(format_rupiah(analysis['total_amount']))}",
        f"📊 Average/day: {escape(format_rupiah(round(analysis['avg_per_day'])))}",
        f"🔺 Highest day: {escape(high_day)} — {escape(format_rupiah(high_amt))}",
        f"🔻 Lowest day: {escape(low_day)} — {escape(format_rupiah(low_amt))}",
    ]
    return "\n".join(lines)


# ── Combined daily digest ─────────────────────────────────────────────────────

def format_daily(events: list[dict], cards: list[dict]) -> str:
    cal_part  = format_events(events, "Today's calendar")
    task_part = format_cards(cards,   "Open tasks")
    return f"{cal_part}\n\n{task_part}"
