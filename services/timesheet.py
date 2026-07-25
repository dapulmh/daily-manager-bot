"""
services/timesheet.py
Lightweight daily timesheet log backed by a local JSON store.
Entries accumulate until explicitly cleared — no scheduler involved.
"""

import json
import uuid
from pathlib import Path

from utils.dt import now

# Use /data volume on Fly.io if it exists, otherwise fall back to local
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(".")
STORE_FILE = _DATA_DIR / "timesheet.json"


# ── Persistence ──────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return []


def _save(entries: list[dict]) -> None:
    STORE_FILE.write_text(json.dumps(entries, indent=2))


# ── Public API ───────────────────────────────────────────────────────────────

def add_entry(description: str, date_iso: str = None) -> dict:
    """Add and persist a timesheet entry. date_iso defaults to today."""
    entry = {
        "id":          str(uuid.uuid4()),
        "date_iso":    date_iso or now().strftime("%Y-%m-%d"),
        "description": description,
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
