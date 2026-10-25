"""
services/notes_insight.py
Classification + brainstorming on top of services/notes.py.

Same non-RAG shape as services/insight.py: deterministic aggregation
(services.notes.aggregate_notes) feeds a single Groq call for generation -
no vector store/embeddings, since the note log is a small local JSON file.

Classification and brainstorm generation both degrade gracefully on
Groq/JSON failures - an outage should never block saving or viewing notes.
"""

from __future__ import annotations

import json
import logging

from groq import Groq

import services.notes as notes_svc
from utils.config import CONFIG

logger = logging.getLogger(__name__)
_client = Groq(api_key=CONFIG["GROQ_API_KEY"])

CATEGORIES = ["idea", "note", "task", "question", "other"]

_CATEGORY_PROMPT = """You are a JSON-only classifier. Classify the note below into exactly one category
from this list: {categories}.

idea     - a new concept, product, project, or creative possibility worth pursuing
note     - a plain observation, fact, or reference info to remember
task     - something actionable the user still needs to do
question - something the user is wondering about / wants an answer to
other    - anything that doesn't clearly fit the above

Return ONLY a valid JSON object with a single key "category", e.g.:
{{"category": "idea"}}

Note:
{text}
"""

_BRAINSTORM_PROMPT = """You are a sharp, encouraging thinking partner helping the user develop their own notes and ideas.
Respond in plain text with no markdown syntax, 6-10 short lines max.

Notes summary:
{context}

{instruction}
"""


def classify_note(text: str) -> str:
    """
    Classify a single note's text into one of CATEGORIES.
    Falls back to "other" on empty input or any Groq/JSON failure - never raises.
    """
    if not text or not text.strip():
        return "other"

    prompt = _CATEGORY_PROMPT.format(categories=", ".join(CATEGORIES), text=text.strip()[:2000])

    try:
        resp = _client.chat.completions.create(
            model=CONFIG["GROQ_MODEL"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        parsed = json.loads(resp.choices[0].message.content.strip())
        category = parsed.get("category")
        return category if category in CATEGORIES else "other"
    except Exception as e:
        logger.error("Groq note classification error: %s", e)
        return "other"


def add_note(text: str) -> dict:
    """One-stop entry point used by the /note command: classify then persist."""
    category = classify_note(text)
    return notes_svc.add_entry(text=text, category=category)


def _build_context(aggregate: dict) -> str:
    lines = [f"Total notes saved: {aggregate['total_count']}"]

    if aggregate.get("by_category"):
        cat_str = ", ".join(
            f"{cat}: {n}" for cat, n in sorted(aggregate["by_category"].items(), key=lambda kv: -kv[1])
        )
        lines.append(f"By category: {cat_str}")

    if aggregate.get("topic"):
        lines.append(f"Topic requested: {aggregate['topic']}")

    pool = aggregate.get("matched") or aggregate.get("recent") or []
    if pool:
        items = "\n".join(f"- [{n['category']}] {n['text']}" for n in pool)
        lines.append(f"Relevant notes:\n{items}")

    return "\n".join(lines)


def generate_brainstorm(aggregate: dict) -> str:
    """
    Generate a natural-language brainstorm from aggregated note stats.
    Never raises - returns a fallback string on failure.
    """
    if aggregate["total_count"] == 0:
        return "No notes saved yet, so there's nothing to brainstorm from."

    topic = aggregate.get("topic")
    instruction = (
        f'Brainstorm specifically about: "{topic}", grounded in the notes above. '
        "Suggest 3-4 concrete next steps, angles, or open questions to explore."
        if topic else
        "Give a short overview of what's been captured, call out any themes or clusters "
        "across the notes, then suggest 2-3 ideas worth following up on."
    )
    prompt = _BRAINSTORM_PROMPT.format(context=_build_context(aggregate), instruction=instruction)

    try:
        resp = _client.chat.completions.create(
            model=CONFIG["GROQ_MODEL"],
            messages=[{"role": "system", "content": prompt}],
            temperature=0.4,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Groq brainstorm generation error: %s", e)
        return "Brainstorm unavailable right now - the analysis service is temporarily unreachable."


def analyze_notes(topic: str | None = None) -> tuple[dict, str]:
    """One-stop entry point used by both the /brainstorm command and the NLP router."""
    entries   = notes_svc.list_entries()
    aggregate = notes_svc.aggregate_notes(entries, topic=topic)
    text      = generate_brainstorm(aggregate)
    return aggregate, text
