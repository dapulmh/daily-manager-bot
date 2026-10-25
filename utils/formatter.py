"""
utils/formatter.py
Builds nicely formatted Telegram messages (MarkdownV2-safe).
"""

from __future__ import annotations

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


def format_expenditure_insight(analysis: dict, insight_text: str) -> str:
    """Stats block (as format_expenditure_analysis) plus category/trend breakdown and an AI insight."""
    if analysis["entry_count"] == 0:
        return "*Expenditure Analysis*\n\n_No entries logged_ 📊"

    lines = [format_expenditure_analysis(analysis)]

    if analysis.get("by_category"):
        lines.append("\n📂 *By category:*")
        for cat, amt in sorted(analysis["by_category"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  • {escape(cat.title())}: {escape(format_rupiah(amt))}")

    if analysis.get("top_expenses"):
        lines.append("\n🏆 *Biggest expenses:*")
        for e in analysis["top_expenses"]:
            lines.append(
                f"  • {escape(e['description'])} — {escape(format_rupiah(e['amount']))} "
                f"\\({escape(e['date_iso'])}\\)"
            )

    trend = analysis.get("trend")
    if trend and trend.get("change_pct") is not None:
        change = trend["change_pct"]
        arrow  = "🔺" if change > 0 else "🔻" if change < 0 else "➖"
        lines.append(f"\n{arrow} 7\\-day trend: {escape(f'{change:+.0f}%')} vs previous week")

    lines.append(f"\n💡 *Insight:*\n{escape(insight_text)}")

    return "\n".join(lines)


# ── Notes ────────────────────────────────────────────────────────────────────

_NOTE_CATEGORY_EMOJI = {
    "idea": "💡", "note": "🗒", "task": "✅", "question": "❓", "other": "📌",
}


def format_notes(entries: list[dict], category: str | None = None) -> str:
    if category:
        entries = [e for e in entries if e.get("category") == category]

        if not entries:
            return f"*Notes — {escape(category.title())}*\n\n_No notes in this category_ 🗒"

        lines = [f"*Notes — {escape(category.title())}*\n"]
        for e in entries:
            lines.append(f"  • {escape(e['text'])}")
        return "\n".join(lines)

    if not entries:
        return "*Notes*\n\n_No notes saved yet_ 🗒"

    by_category: dict[str, list[dict]] = {}
    for e in entries:
        by_category.setdefault(e.get("category") or "other", []).append(e)

    lines = ["*Notes*\n"]
    for cat in sorted(by_category):
        emoji = _NOTE_CATEGORY_EMOJI.get(cat, "📌")
        lines.append(f"{emoji} *{escape(cat.title())}*")
        for e in by_category[cat]:
            lines.append(f"  • {escape(e['text'])}")

    return "\n".join(lines)


def format_notes_insight(aggregate: dict, insight_text: str) -> str:
    """Stats block (total + category breakdown) plus an AI brainstorm trailer."""
    if aggregate["total_count"] == 0:
        return "*Notes Brainstorm*\n\n_No notes saved yet_ 🗒"

    lines = ["*Notes Brainstorm*\n"]
    if aggregate.get("topic"):
        lines.append(f"🎯 Topic: {escape(aggregate['topic'])}")
    lines.append(f"🗒 Total notes: {aggregate['total_count']}")

    if aggregate.get("by_category"):
        lines.append("\n📂 *By category:*")
        for cat, count in sorted(aggregate["by_category"].items(), key=lambda kv: -kv[1]):
            emoji = _NOTE_CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"  • {emoji} {escape(cat.title())}: {count}")

    if aggregate.get("matched") is not None:
        lines.append(f"\n🔎 {len(aggregate['matched'])} note\\(s\\) matched the topic")

    lines.append(f"\n💡 *Brainstorm:*\n{escape(insight_text)}")

    return "\n".join(lines)


# ── Combined daily digest ─────────────────────────────────────────────────────

def format_daily(events: list[dict], cards: list[dict]) -> str:
    cal_part  = format_events(events, "Today's calendar")
    task_part = format_cards(cards,   "Open tasks")
    return f"{cal_part}\n\n{task_part}"
