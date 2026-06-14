"""
services/trello.py
Wraps the Trello REST API using API key + token (no OAuth needed).
"""

from __future__ import annotations

import requests
from utils.config import CONFIG

BASE = "https://api.trello.com/1"

PRIORITY_COLORS = {
    "high":   "red",
    "medium": "yellow",
    "low":    "green",
}

# Label name → label id cache (populated on first use)
_label_cache: dict[str, str] = {}
# List name → list id cache
_list_cache: dict[str, str] = {}


def _auth() -> dict:
    return {"key": CONFIG["TRELLO_API_KEY"], "token": CONFIG["TRELLO_TOKEN"]}


# ── Lists ────────────────────────────────────────────────────────────────────

def get_lists() -> list[dict]:
    r = requests.get(f"{BASE}/boards/{CONFIG['TRELLO_BOARD_ID']}/lists", params=_auth())
    r.raise_for_status()
    return r.json()


def _list_id(name: str) -> str | None:
    """Return list id by name (case-insensitive). Cached."""
    if name not in _list_cache:
        for lst in get_lists():
            _list_cache[lst["name"].lower()] = lst["id"]
    return _list_cache.get(name.lower())


def default_list_id() -> str:
    """Return the first list on the board (usually 'To Do')."""
    lists = get_lists()
    return lists[0]["id"] if lists else ""


# ── Labels ───────────────────────────────────────────────────────────────────

def get_labels() -> list[dict]:
    r = requests.get(f"{BASE}/boards/{CONFIG['TRELLO_BOARD_ID']}/labels", params=_auth())
    r.raise_for_status()
    return r.json()


def _ensure_label(priority: str) -> str:
    """Get or create a label for the given priority. Returns label id."""
    if priority in _label_cache:
        return _label_cache[priority]

    color = PRIORITY_COLORS.get(priority, "blue")
    for lbl in get_labels():
        if lbl.get("color") == color:
            _label_cache[priority] = lbl["id"]
            return lbl["id"]

    # Create it
    r = requests.post(f"{BASE}/labels", params={
        **_auth(), "name": priority.capitalize(),
        "color": color, "idBoard": CONFIG["TRELLO_BOARD_ID"],
    })
    r.raise_for_status()
    lbl_id = r.json()["id"]
    _label_cache[priority] = lbl_id
    return lbl_id


# ── Cards ────────────────────────────────────────────────────────────────────

def get_cards(list_name: str = None) -> list[dict]:
    """Return cards on the board, optionally filtered to a list name."""
    if list_name:
        lid = _list_id(list_name)
        if not lid:
            return []
        r = requests.get(f"{BASE}/lists/{lid}/cards", params=_auth())
    else:
        r = requests.get(
            f"{BASE}/boards/{CONFIG['TRELLO_BOARD_ID']}/cards",
            params=_auth(),
        )
    r.raise_for_status()
    return r.json()


def create_card(name: str, description: str = "",
                priority: str = None, due: str = None,
                list_name: str = None) -> dict:
    """Create a Trello card. Returns the created card dict."""
    lid = _list_id(list_name) if list_name else default_list_id()

    params = {**_auth(), "name": name, "idList": lid}
    if description:
        params["desc"] = description
    if due:
        params["due"] = due

    r = requests.post(f"{BASE}/cards", params=params)
    r.raise_for_status()
    card = r.json()

    if priority:
        label_id = _ensure_label(priority)
        requests.post(f"{BASE}/cards/{card['id']}/idLabels",
                      params={**_auth(), "value": label_id})

    return card


def move_card(card_id: str, list_name: str) -> dict:
    lid = _list_id(list_name)
    if not lid:
        raise ValueError(f"List '{list_name}' not found on board")
    r = requests.put(f"{BASE}/cards/{card_id}",
                     params={**_auth(), "idList": lid})
    r.raise_for_status()
    return r.json()


def set_card_priority(card_id: str, priority: str) -> None:
    label_id = _ensure_label(priority)
    # Remove existing priority labels first
    card_r = requests.get(f"{BASE}/cards/{card_id}", params=_auth())
    card = card_r.json()
    for lbl in card.get("labels", []):
        if lbl.get("color") in PRIORITY_COLORS.values():
            requests.delete(f"{BASE}/cards/{card_id}/idLabels/{lbl['id']}",
                            params=_auth())
    requests.post(f"{BASE}/cards/{card_id}/idLabels",
                  params={**_auth(), "value": label_id})


def delete_card(card_id: str) -> None:
    requests.delete(f"{BASE}/cards/{card_id}", params=_auth()).raise_for_status()
