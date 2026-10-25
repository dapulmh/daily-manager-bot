"""
services/notes.py
Lightweight notes/ideas log backed by a local JSON store.
Entries accumulate until explicitly cleared — no scheduler involved.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from utils.dt import now

# Use /data volume on Fly.io if it exists, otherwise fall back to local
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(".")
STORE_FILE = _DATA_DIR / "notes.json"

RECENT_LIMIT = 20


# ── Persistence ──────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return []


def _save(entries: list[dict]) -> None:
    STORE_FILE.write_text(json.dumps(entries, indent=2))


# ── Public API ───────────────────────────────────────────────────────────────

def add_entry(text: str, category: str) -> dict:
    """Add and persist a note entry."""
    entry = {
        "id":             str(uuid.uuid4()),
        "text":           text,
        "category":       category,
        "created_at_iso": now().isoformat(),
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    return entry


def list_entries() -> list[dict]:
    return _load()


def clear_entries() -> int:
    entries = _load()
    count = len(entries)
    _save([])
    return count


def aggregate_notes(entries: list[dict], topic: str | None = None) -> dict:
    """
    Pure function - deterministic retrieval for /brainstorm, mirrors
    services.expenditure.analyze_entries. No embeddings/vector search:
    "relevance" is a case-insensitive substring match against note text,
    plus an exact match against a category name.
    """
    by_category: dict[str, int] = {}
    for entry in entries:
        category = entry.get("category") or "other"
        by_category[category] = by_category.get(category, 0) + 1

    recent = sorted(entries, key=lambda e: e["created_at_iso"], reverse=True)[:RECENT_LIMIT]

    matched = None
    if topic:
        needle = topic.lower().strip()
        matched = [
            e for e in entries
            if needle in e["text"].lower() or e.get("category") == needle
        ]
        if not matched:
            matched = recent

    return {
        "total_count": len(entries),
        "by_category": by_category,
        "recent":       recent,
        "matched":      matched,
        "topic":        topic,
    }
