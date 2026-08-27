"""
services/expenditure.py
Lightweight daily expenditure log backed by a local JSON store.
Entries accumulate until explicitly cleared — no scheduler involved.
"""

import json
import uuid
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
        }

    per_day: dict[str, int] = {}
    for entry in entries:
        per_day[entry["date_iso"]] = per_day.get(entry["date_iso"], 0) + entry["amount"]

    total_amount = sum(per_day.values())
    total_days   = len(per_day)
    dates        = sorted(per_day)

    return {
        "total_days":   total_days,
        "entry_count":  len(entries),
        "per_day":      per_day,
        "total_amount": total_amount,
        "avg_per_day":  total_amount / total_days,
        "highest_day":  max(per_day.items(), key=lambda kv: kv[1]),
        "lowest_day":   min(per_day.items(), key=lambda kv: kv[1]),
        "date_range":   (dates[0], dates[-1]),
    }
