# Graph Report - daily-manager-bot  (2026-08-28)

## Corpus Check
- Corpus is ~7,130 words - fits in a single context window. You may not need a graph.

## Summary
- 180 nodes · 414 edges · 17 communities (16 shown, 1 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 20 edges (avg confidence: 0.85)
- Token cost: 86,693 input · 0 output

## Community Hubs (Navigation)
- Google Calendar & NLP Core
- Message Handling & Formatting
- Trello Cards & Callbacks
- Bot Entrypoint & Commands
- Module Overview & Duplication
- Secrets & Configuration
- Timesheet Logging
- Reminders Service
- Scheduler Init & Persistence
- Deployment (Fly vs Oracle)
- Calendar Deps & Test Cleanup
- Trello Service Internals
- Groq NLP Intent Flow
- Config Loader

## God Nodes (most connected - your core abstractions)
1. `handle_message()` - 23 edges
2. `Daily Manager Bot (README overview)` - 20 edges
3. `escape()` - 16 edges
4. `private_only()` - 14 edges
5. `now()` - 14 edges
6. `timesheet()` - 12 edges
7. `parse_intent()` - 12 edges
8. `Daily Manager Bot (Project Overview)` - 12 edges
9. `main()` - 11 edges
10. `today()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `parse_intent()` --rationale_for--> `NLP Failure Graceful Degradation`  [EXTRACTED]
  services/nlp.py → CLAUDE.md
- `parse_intent()` --references--> `SYSTEM_PROMPT (intent schema)`  [EXTRACTED]
  services/nlp.py → CLAUDE.md
- `utils/formatter.py` --references--> `escape()`  [EXTRACTED]
  CLAUDE.md → utils/formatter.py
- `handle_message()` --rationale_for--> `NLP Failure Graceful Degradation`  [EXTRACTED]
  handlers/nlp.py → CLAUDE.md
- `handlers/commands.py` --references--> `private_only()`  [EXTRACTED]
  CLAUDE.md → utils/auth.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Three-Layer Architecture (handlers/services/utils)** — bot_module, handlers_commands_module, services_trello_module, utils_config_module [EXTRACTED 1.00]
- **Dual Deployment Paths: Fly.io (CI) vs Oracle Cloud (manual systemd)** — github_workflows_fly_deploy_fly_deploy_workflow, fly_config, readme_daily_manager_bot_service, readme_oracle_cloud [EXTRACTED 1.00]
- **NLP Intent Parsing Pipeline** — handlers_nlp_handle_message, services_nlp_parse_intent, services_nlp_system_prompt, claude_nlp_failure_degradation [EXTRACTED 1.00]

## Communities (17 total, 1 thin omitted)

### Community 0 - "Google Calendar & NLP Core"
Cohesion: 0.12
Nodes (25): datetime, create_event(), delete_event(), get_events(), _get_service(), services/google_calendar.py Wraps the Google Calendar API. Auth uses OAuth2…, Return events for 'today' or 'week'., Create a calendar event. Returns the created event dict. (+17 more)

### Community 1 - "Message Handling & Formatting"
Cohesion: 0.21
Nodes (20): NLP Failure Graceful Degradation, handlers/commands.py All /command handlers., handle_message(), DEFAULT_TYPE, Update, handlers/nlp.py Handles free-text messages — parses intent and routes to the…, test_formatter(), utils/auth.py Simple decorator that rejects any user who isn't you. (+12 more)

### Community 2 - "Trello Cards & Callbacks"
Cohesion: 0.16
Nodes (21): handle_callback(), DEFAULT_TYPE, Update, handlers/callbacks.py Handles InlineKeyboardButton presses (priority picker,…, _auth(), create_card(), default_list_id(), delete_card() (+13 more)

### Community 3 - "Bot Entrypoint & Commands"
Cohesion: 0.20
Nodes (20): AsyncIOScheduler, main(), _post_init(), Daily Manager Bot — entry point Starts the Telegram bot with polling., Single-User Private-Only Auth Model, add_event(), add_task(), DEFAULT_TYPE (+12 more)

### Community 4 - "Module Overview & Duplication"
Cohesion: 0.25
Nodes (11): bot.py (Entry Point), Duplicated Intent-to-Service Logic (commands vs nlp), handlers/callbacks.py, handlers/commands.py, handlers/nlp.py, Daily Manager Bot (README overview), pytz==2024.2, SYSTEM_PROMPT (intent schema) (+3 more)

### Community 5 - "Secrets & Configuration"
Cohesion: 0.24
Nodes (10): Daily Manager Bot (Project Overview), Secrets Handling Policy (never commit/print creds), Telegram, credentials.json, .env (secrets file), fly.toml (Fly.io app config), python-dotenv==1.0.1, python-telegram-bot==21.6 (+2 more)

### Community 6 - "Timesheet Logging"
Cohesion: 0.36
Nodes (9): /timesheet — show logged entries /timesheet clear — clear all entries…, timesheet(), add_entry(), clear_entries(), list_entries(), _load(), services/timesheet.py Lightweight daily timesheet log backed by a local JSON…, Add and persist a timesheet entry. date_iso defaults to today. (+1 more)

### Community 7 - "Reminders Service"
Cohesion: 0.40
Nodes (9): add_reminder(), clear_all_reminders(), _fire_reminder(), list_reminders(), _load(), services/reminders.py Lightweight reminder system using APScheduler + a local…, Add and persist a reminder. recurrence: 'daily' | 'weekly' | None., _save() (+1 more)

### Community 8 - "Scheduler Init & Persistence"
Cohesion: 0.29
Nodes (8): init_scheduler() (post_init hook), Reminders Durability via APScheduler + JSON Store, Shared /data Path Resolution (local vs Fly), reminders.json, APScheduler==3.10.4, services/reminders.py, services/timesheet.py, timesheet.json

### Community 9 - "Deployment (Fly vs Oracle)"
Cohesion: 0.29
Nodes (7): Fly.io, deploy job, FLY_API_TOKEN secret, Fly Deploy GitHub Actions Workflow, flyctl deploy --remote-only step, daily-manager-bot.service (systemd unit), Oracle Cloud Always Free

### Community 10 - "Calendar Deps & Test Cleanup"
Cohesion: 0.29
Nodes (7): Google Calendar, google-api-python-client==2.139.0, google-auth-httplib2==0.2.0, google-auth-oauthlib==1.2.1, services/google_calendar.py, _cleanup() (test teardown), test_local.py (integration tests)

### Community 11 - "Trello Service Internals"
Cohesion: 0.29
Nodes (7): Trello, Trello Priority-via-Label-Color Model, requests==2.32.3, _label_cache, _list_cache, services/trello.py, TRELLO_DONE_LIST config var

### Community 12 - "Groq NLP Intent Flow"
Cohesion: 0.40
Nodes (5): Groq, NLP Intent Flow Design, groq==0.11.0, httpx==0.27.2, services/nlp.py

## Knowledge Gaps
- **16 isolated node(s):** `services/timesheet.py`, `utils/auth.py`, `fly.toml (Fly.io app config)`, `CONFIG dict`, `_label_cache` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `escape()` connect `Message Handling & Formatting` to `Google Calendar & NLP Core`, `Bot Entrypoint & Commands`, `Module Overview & Duplication`, `Secrets & Configuration`, `Timesheet Logging`?**
  _High betweenness centrality (0.282) - this node is a cross-community bridge._
- **Why does `Daily Manager Bot (README overview)` connect `Module Overview & Duplication` to `Secrets & Configuration`, `Scheduler Init & Persistence`, `Deployment (Fly vs Oracle)`, `Calendar Deps & Test Cleanup`, `Trello Service Internals`, `Groq NLP Intent Flow`?**
  _High betweenness centrality (0.250) - this node is a cross-community bridge._
- **Why does `handle_message()` connect `Message Handling & Formatting` to `Google Calendar & NLP Core`, `Trello Cards & Callbacks`, `Bot Entrypoint & Commands`, `Timesheet Logging`, `Reminders Service`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **What connects `services/timesheet.py`, `utils/auth.py`, `fly.toml (Fly.io app config)` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Google Calendar & NLP Core` be split into smaller, more focused modules?**
  _Cohesion score 0.12121212121212122 - nodes in this community are weakly interconnected._