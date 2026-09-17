"""
services/insight.py
Expense insight generation on top of services/expenditure.py.

This is deliberately NOT a vector-store RAG pipeline - the expenditure log is a
small local JSON file, not a document corpus, so a vector DB/embeddings would
add infra cost for no benefit. Instead this follows the same shape (retrieve
relevant context, then generate a natural-language answer from it):
  - "retrieval" is deterministic aggregation (services.expenditure.analyze_entries)
  - "generation" is a single Groq call fed that compact, structured context

Category classification and insight generation both degrade gracefully on
Groq/JSON failures - an insight-generation outage should never block viewing
raw expenditure stats.
"""

from __future__ import annotations

import json
import logging

from groq import Groq

import services.expenditure as expenditure_svc
from utils.config import CONFIG
from utils.formatter import format_rupiah

logger = logging.getLogger(__name__)
_client = Groq(api_key=CONFIG["GROQ_API_KEY"])

CATEGORIES = ["food", "transport", "bills", "shopping", "entertainment", "health", "other"]

_CATEGORY_PROMPT = """You are a JSON-only classifier. Classify each numbered expense description
into exactly one category from this list: {categories}.

Return ONLY a valid JSON object mapping the number (as a string) to its category, e.g.:
{{"0": "food", "1": "transport"}}

Descriptions:
{items}
"""

_INSIGHT_PROMPT = """You are a concise personal finance coach reviewing the user's spending data below.
Respond in plain text with no markdown syntax, 5-8 short lines max.

Spending summary:
{context}

{instruction}
"""


def classify_categories(entries: list[dict]) -> dict[str, str]:
    """
    Classify a batch of expenditure entries (each needs 'id' and 'description').
    Returns {entry_id: category}. Falls back to "other" for anything the model
    fails to classify, and returns {} entirely on a hard API/parse failure.
    """
    if not entries:
        return {}

    items  = "\n".join(f"{i}. {e['description']}" for i, e in enumerate(entries))
    prompt = _CATEGORY_PROMPT.format(categories=", ".join(CATEGORIES), items=items)

    try:
        resp = _client.chat.completions.create(
            model=CONFIG["GROQ_MODEL"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        by_index = json.loads(resp.choices[0].message.content.strip())
    except Exception as e:
        logger.error("Groq category classification error: %s", e)
        return {}

    return {
        entry["id"]: by_index.get(str(i)) if by_index.get(str(i)) in CATEGORIES else "other"
        for i, entry in enumerate(entries)
    }


def categorize_missing(entries: list[dict]) -> list[dict]:
    """
    Ensure every entry has a category, classifying and persisting any that
    don't (amortizes classification cost - only new/uncategorized entries are
    ever sent to Groq). Returns the full, up-to-date entry list.
    """
    missing = expenditure_svc.entries_missing_category(entries)
    if not missing:
        return entries

    category_map = classify_categories(missing)
    if not category_map:
        return entries  # classification failed - proceed uncategorized rather than blocking analysis

    return expenditure_svc.update_categories(category_map)


def _build_context(analysis: dict) -> str:
    lines = [
        f"Date range: {analysis['date_range'][0]} to {analysis['date_range'][1]}",
        f"Total spent: {format_rupiah(analysis['total_amount'])} across "
        f"{analysis['total_days']} day(s), {analysis['entry_count']} entries",
        f"Average per day: {format_rupiah(round(analysis['avg_per_day']))}",
        f"Highest day: {analysis['highest_day'][0]} ({format_rupiah(analysis['highest_day'][1])})",
        f"Lowest day: {analysis['lowest_day'][0]} ({format_rupiah(analysis['lowest_day'][1])})",
    ]

    if analysis.get("by_category"):
        cat_str = ", ".join(
            f"{cat}: {format_rupiah(amt)}"
            for cat, amt in sorted(analysis["by_category"].items(), key=lambda kv: -kv[1])
        )
        lines.append(f"By category: {cat_str}")

    if analysis.get("top_expenses"):
        top_str = ", ".join(
            f"{e['description']} ({format_rupiah(e['amount'])})" for e in analysis["top_expenses"]
        )
        lines.append(f"Largest single expenses: {top_str}")

    trend = analysis.get("trend")
    if trend:
        change = trend.get("change_pct")
        change_str = f"{change:+.0f}%" if change is not None else "n/a (not enough history)"
        lines.append(
            f"Last 7 days: {format_rupiah(trend['last_7_total'])} vs previous 7 days: "
            f"{format_rupiah(trend['prev_7_total'])} (change: {change_str})"
        )

    return "\n".join(lines)


def generate_insight(analysis: dict, question: str | None = None) -> str:
    """
    Generate a natural-language insight from aggregated expenditure stats.
    If `question` is given, answers that specific question instead of giving
    the generic overview. Never raises - returns a fallback string on failure.
    """
    if analysis["entry_count"] == 0:
        return "No expenses logged yet, so there's nothing to analyze."

    instruction = (
        f'Answer this question based only on the data above: "{question}"'
        if question else
        "Give a short overview of spending patterns, call out anything notable, "
        "then 2-3 concrete, specific suggestions to spend less or save more."
    )
    prompt = _INSIGHT_PROMPT.format(context=_build_context(analysis), instruction=instruction)

    try:
        resp = _client.chat.completions.create(
            model=CONFIG["GROQ_MODEL"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0.4,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Groq insight generation error: %s", e)
        return "Insight unavailable right now - the analysis service is temporarily unreachable."


def analyze_with_insight(question: str | None = None) -> tuple[dict, str]:
    """One-stop entry point used by both the /analysis command and the NLP router."""
    entries      = categorize_missing(expenditure_svc.list_entries())
    analysis     = expenditure_svc.analyze_entries(entries)
    insight_text = generate_insight(analysis, question=question)
    return analysis, insight_text
