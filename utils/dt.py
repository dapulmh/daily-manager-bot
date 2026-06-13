"""
utils/dt.py
Date/time helpers — always timezone-aware using the configured TZ.
"""

from datetime import datetime, timedelta
import pytz
from utils.config import CONFIG

TZ = pytz.timezone(CONFIG["TIMEZONE"])


def now() -> datetime:
    return datetime.now(TZ)


def today_range():
    """Return (start, end) for today in UTC ISO format (for Google API)."""
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def week_range():
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=7)
    return start.isoformat(), end.isoformat()


def fmt_dt(iso_str: str) -> str:
    """Format an ISO datetime string to a human-readable local string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local = dt.astimezone(TZ)
        return local.strftime("%-d %b, %H:%M")
    except Exception:
        return iso_str


def fmt_date(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local = dt.astimezone(TZ)
        return local.strftime("%-d %b")
    except Exception:
        return iso_str
