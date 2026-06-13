# Daily Manager Bot

A zero-cost personal productivity Telegram bot that integrates Google Calendar and Trello with natural language support.

## Stack

| Layer | Tool | Cost |
|---|---|---|
| Bot framework | python-telegram-bot | Free |
| NLP / intent parsing | Groq (Llama 3) | Free |
| Calendar | Google Calendar API | Free |
| Tasks | Trello API | Free |
| Reminders | APScheduler (in-process) | Free |
| Hosting (prod) | Oracle Cloud Always Free | Free |

---

## Project structure

```
daily-manager-bot/
├── bot.py                  # Entry point
├── requirements.txt
├── .env                    # Your secrets (never commit this)
├── .env.example            # Template
├── credentials.json        # Google OAuth2 creds (downloaded from GCP)
├── token.json              # Auto-generated after first Google auth
├── reminders.json          # Auto-generated, persists reminders
├── daily-manager-bot.service  # systemd unit for Oracle Cloud
│
├── handlers/
│   ├── commands.py         # /start /today /week /add /task /remind
│   ├── nlp.py              # Free-text message handler
│   └── callbacks.py        # Inline button actions
│
├── services/
│   ├── google_calendar.py  # Google Calendar CRUD
│   ├── trello.py           # Trello CRUD
│   ├── nlp.py              # Groq intent parser
│   └── reminders.py        # APScheduler + JSON store
│
└── utils/
    ├── config.py           # Loads .env
    ├── auth.py             # Private-only decorator
    ├── dt.py               # Timezone-aware datetime helpers
    └── formatter.py        # Telegram MarkdownV2 message builder
```

---

## Setup — Step by step

### 1. Telegram bot token

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token → `TELEGRAM_TOKEN` in `.env`
4. Find your user ID: search **@userinfobot**, send `/start` → copy your ID → `ALLOWED_USER_ID`

### 2. Google Calendar credentials

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable **Google Calendar API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the JSON → rename to `credentials.json`, put in project root
7. First run will open a browser for OAuth consent — after that `token.json` is auto-created

### 3. Trello API key + token

1. Go to https://trello.com/power-ups/admin
2. Create a new Power-Up → copy **API Key** → `TRELLO_API_KEY`
3. Visit `https://trello.com/1/authorize?key=YOUR_KEY&scope=read,write&expiration=never&name=DailyManagerBot&response_type=token`
4. Authorise → copy the token → `TRELLO_TOKEN`
5. Find your board ID: open your board in browser → the URL is `trello.com/b/<BOARD_ID>/...`

### 4. Groq API key (free)

1. Go to https://console.groq.com/
2. Sign up (free, no credit card needed)
3. Create an API key → `GROQ_API_KEY`

### 5. Local development

```bash
# Clone / enter project
cd daily-manager-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your credentials
cp .env.example .env
# Edit .env with your values

# Run the bot
python bot.py
```

---

## Production deployment on Oracle Cloud Always Free

### Provision a VM

1. Sign up at https://cloud.oracle.com/ (Always Free, credit card for identity only)
2. Create an **Ampere A1** VM (ARM): 1 OCPU, 6 GB RAM, Ubuntu 22.04
3. Open port 443/80 in the security list if you plan to use webhooks (polling is fine too)

### Deploy

```bash
# SSH into your VM
ssh ubuntu@<your-vm-ip>

# Install Python 3.11+
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git

# Clone your repo
git clone https://github.com/youruser/daily-manager-bot.git
cd daily-manager-bot

# Set up venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy your .env and credentials.json via scp (from your Mac):
# scp .env ubuntu@<ip>:~/daily-manager-bot/
# scp credentials.json ubuntu@<ip>:~/daily-manager-bot/
# scp token.json ubuntu@<ip>:~/daily-manager-bot/   # after running locally once

# Install and enable systemd service
sudo cp daily-manager-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable daily-manager-bot
sudo systemctl start daily-manager-bot

# Check logs
sudo journalctl -u daily-manager-bot -f
```

---

## Commands reference

| Command | Example | What it does |
|---|---|---|
| `/start` | `/start` | Show help |
| `/today` | `/today` | Today's calendar + open Trello cards |
| `/week` | `/week` | This week's calendar |
| `/add` | `/add Dentist at 2pm tomorrow` | Create a calendar event (NLP parsed) |
| `/task` | `/task Fix login bug #high` | Create a Trello card |
| `/remind` | `/remind` | List all reminders |
| `/remind clear` | `/remind clear` | Delete all reminders |

### Natural language examples

- *"what's on my schedule today"*
- *"add a meeting with the team at 10am on Friday"*
- *"create a task: refactor the API, high priority"*
- *"remind me to call the bank at 4pm"*
- *"show me this week"*

---

## Extending the bot

### Add a new command

1. Add a handler function in `handlers/commands.py`
2. Register it in `bot.py` with `app.add_handler(CommandHandler(...))`

### Add a new NLP intent

1. Add the intent name and its `data` schema to the `SYSTEM_PROMPT` in `services/nlp.py`
2. Add a routing branch in `handlers/nlp.py`

### Add a new service (e.g. Notion, Todoist)

1. Create `services/notion.py` following the same pattern as `trello.py`
2. Add credentials to `utils/config.py` and `.env.example`
3. Wire it into the relevant handlers
