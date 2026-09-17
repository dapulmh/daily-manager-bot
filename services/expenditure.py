"""
services/expenditure.py
Lightweight daily expenditure log backed by a local JSON store.
Entries accumulate until explicitly cleared — no scheduler involved.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from utils.dt import now

# Use /data volume on Fly.io if it exists, otherwise fall back to local
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(".")
STORE_FILE = _DATA_DIR / "expenditure.json"


# ── Persistence ──────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return []


def _save(entries: list[dict]) -> None:
    STORE_FILE.write_text(json.dumps(entries, indent=2))


# ── Public API ───────────────────────────────────────────────────────────────

def add_entry(description: str, amount: int, date_iso: str = None) -> dict:
    """Add and persist an expenditure entry. date_iso defaults to today."""
    entry = {
        "id":            str(uuid.uuid4()),
        "date_iso":      date_iso or now().strftime("%Y-%m-%d"),
        "description":   description,
        "amount":        amount,
        "logged_at_iso": now().isoformat(),
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


def entries_missing_category(entries: list[dict]) -> list[dict]:
    """Entries that haven't been classified into a spending category yet."""
    return [e for e in entries if not e.get("category")]


def update_categories(category_map: dict[str, str]) -> list[dict]:
    """
    Persist category assignments for existing entries by id (immutable update -
    builds new entry dicts rather than mutating the loaded ones). Returns the
    full, updated entry list.
    """
    entries = _load()
    updated = [
        {**e, "category": category_map[e["id"]]} if e["id"] in category_map else e
        for e in entries
    ]
    _save(updated)
    return updated


def _compute_trend(per_day: dict[str, int]) -> dict:
    """Compare total spend in the last 7 days against the 7 days before that."""
    today  = now().date()
    last_7 = 0
    prev_7 = 0
    for date_str, amount in per_day.items():
        days_ago = (today - datetime.strptime(date_str, "%Y-%m-%d").date()).days
        if 0 <= days_ago < 7:
            last_7 += amount
        elif 7 <= days_ago < 14:
            prev_7 += amount

    change_pct = ((last_7 - prev_7) / prev_7 * 100) if prev_7 else None
    return {"last_7_total": last_7, "prev_7_total": prev_7, "change_pct": change_pct}


def analyze_entries(entries: list[dict]) -> dict:
    """Pure function - computes summary stats over a list of entries."""
    if not entries:
        return {
            "total_days":   0,
            "entry_count":  0,
            "per_day":      {},
            "total_amount": 0,
            "avg_per_day":  0,
            "highest_day":  None,
            "lowest_day":   None,
            "date_range":   None,
            "by_category":  {},
            "top_expenses": [],
            "trend":        None,
        }

    per_day: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for entry in entries:
        per_day[entry["date_iso"]] = per_day.get(entry["date_iso"], 0) + entry["amount"]
        category = entry.get("category") or "other"
        by_category[category] = by_category.get(category, 0) + entry["amount"]

    total_amount = sum(per_day.values())
    total_days   = len(per_day)
    dates        = sorted(per_day)

    top_expenses = [
        {"description": e["description"], "amount": e["amount"], "date_iso": e["date_iso"]}
        for e in sorted(entries, key=lambda e: -e["amount"])[:3]
    ]

    return {
        "total_days":   total_days,
        "entry_count":  len(entries),
        "per_day":      per_day,
        "total_amount": total_amount,
        "avg_per_day":  total_amount / total_days,
        "highest_day":  max(per_day.items(), key=lambda kv: kv[1]),
        "lowest_day":   min(per_day.items(), key=lambda kv: kv[1]),
        "date_range":   (dates[0], dates[-1]),
        "by_category":  by_category,
        "top_expenses": top_expenses,
        "trend":        _compute_trend(per_day),
    }
