# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user Telegram bot ("Daily Manager Bot") that integrates Google Calendar and Trello, with Groq-powered
natural language intent parsing. Runs as one long-lived Python process (long polling, not webhooks). Designed to
run at zero cost: free tiers of Telegram, Google Calendar, Trello, and Groq, deployed on Fly.io.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_TOKEN, ALLOWED_USER_ID, TRELLO_*, GROQ_API_KEY; credentials.json for Google

# Run the bot locally
python bot.py

# Integration tests — hit real Google Calendar/Trello/Groq APIs, no mocks.
# Any events/cards created during a run are deleted again at the end (see _cleanup in test_local.py).
python test_local.py            # all sections
python test_local.py gcal       # gcal | trello | reminders | timesheet | nlp | formatter
```

There is no unit test framework, linter, or type checker configured — `test_local.py` is the only test entry
point, and it is a live integration test, not something to run in CI against fake credentials.

## Deployment

- Deployed to Fly.io (`fly.toml`), single shared-cpu 256mb VM in `sin` (Singapore), app runs out of a `/data`
  volume mount that persists `credentials.json`, `token.json`, `reminders.json`, and `timesheet.json` across
  deploys/restarts.
- `.github/workflows/fly-deploy.yml` auto-deploys on push to `main` via `flyctl deploy --remote-only` (needs
  `FLY_API_TOKEN` secret).
- `services/reminders.py` and `services/timesheet.py` both resolve their JSON store path to `/data/*.json` if
  `/data` exists, else fall back to the repo root — this is what makes local dev and Fly deployment share code
  without config.
- The original README also documents a manual systemd/Oracle-Cloud deployment path (`daily-manager-bot.service`)
  as an alternative to Fly; that path is not exercised by CI.

## Architecture

Three-layer structure, all wired together in `bot.py`:

- `handlers/` — Telegram-facing layer. `commands.py` has one `@private_only` async function per slash command
  (`/start /today /week /add /task /remind /timesheet`). `nlp.py` has a single `handle_message` that runs any
  non-command text through `parse_intent` and branches on `intent` to call the same services the command handlers
  use. `callbacks.py` handles inline-keyboard button presses (`priority:<card_id>:<priority>`,
  `move:<card_id>:<list_name>`).
- `services/` — integration layer, one module per external system (`google_calendar.py`, `trello.py`, `nlp.py`).
  `reminders.py` and `timesheet.py` are self-contained JSON-file-backed stores with no external API.
- `utils/` — `config.py` (loads/validates env vars into a single `CONFIG` dict, raises `EnvironmentError` if a
  required var is missing), `auth.py` (`@private_only` decorator rejects any Telegram user whose id doesn't match
  `ALLOWED_USER_ID` — this is the *only* auth mechanism, the bot has no concept of multiple users), `dt.py`
  (timezone-aware datetime helpers, everything is normalized to `TIMEZONE` from config), `formatter.py` (builds
  Telegram MarkdownV2 strings — all user-facing text must go through `escape()` here before interpolation into a
  MarkdownV2 message, since Telegram will reject or mis-render unescaped special characters).

Both `handlers/commands.py` and `handlers/nlp.py` duplicate the same intent-to-service-call logic (one path for
explicit slash commands, one path for free-text NLP routing) — when adding a new capability, both call sites
typically need updating, plus the `SYSTEM_PROMPT` intent schema in `services/nlp.py`.

### NLP intent flow

`services/nlp.py` sends a system prompt (defining a fixed set of intents and a JSON output schema) plus the raw
user message to Groq, and expects back a strict JSON object `{intent, confidence, data}`. `handlers/nlp.py`
rejects anything with `confidence < 0.6` (except `view_today`) with a fallback help message. Any Groq/JSON error
degrades to `{"intent": "unknown", "confidence": 0, "data": {}}` rather than raising — NLP failures should never
crash the bot.

### Trello priority model

Trello has no native priority field, so `services/trello.py` maps priority to label color (`high`→red,
`medium`→yellow, `low`→green) and lazily creates/caches label and list IDs by name (`_label_cache`, `_list_cache`
module-level dicts, populated on first use per process). `TRELLO_DONE_LIST` (default `"Done"`) is filtered out of
`/today` and NLP task listings so completed cards don't clutter daily views.

### Reminders scheduling

`services/reminders.py` wraps APScheduler's `AsyncIOScheduler`. One-time reminders use a `date` trigger; `daily`/
`weekly` recurrence uses `CronTrigger`. The scheduler is initialized once in `bot.py`'s `post_init` hook
(`init_scheduler`), and on startup re-schedules every reminder found in the JSON store — this is what makes
reminders durable across restarts/redeploys. Only one-time reminders are deleted from the store after firing;
recurring ones persist indefinitely.

## Secrets and credentials

`credentials.json` (Google OAuth client) and `token.json` (auto-generated after first Google auth) are gitignored
but exist in the working tree for local dev — never commit changes that add these to git, and never print their
contents. `.env` holds `TELEGRAM_TOKEN`, `TRELLO_API_KEY`/`TRELLO_TOKEN`, `GROQ_API_KEY` — same rule.
