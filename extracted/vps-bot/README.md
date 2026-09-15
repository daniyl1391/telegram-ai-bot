# 🖥 Telegram Windows VPS Bot

A production-ready Telegram bot that provisions **Windows VPS** instances on demand via a configurable VPS provider API.  
Users interact with the bot in **private chat** to create, monitor, reboot, and delete their virtual servers. RDP credentials are delivered securely and never logged or stored in plain text.

---

## ✨ Features

- `/start` `/help` — Usage guide and rules
- `/create` — Provision a new Windows VPS (with confirmation step)
- `/status` — List your active servers
- `/reboot SERVER_ID` — Reboot a server you own
- `/delete SERVER_ID` — Destroy a server you own
- `/cancel` — Cancel any pending operation
- **Ownership isolation** — users can only manage their own servers
- **Rate limiting** — per-user cooldown on server creation
- **Audit logging** — every create / reboot / delete is recorded
- **Encrypted password storage** — Fernet encryption (or skip storage entirely)
- **Provider abstraction** — swap providers without touching bot logic
- **Docker + Railway** ready — deploy with a single click
- **Graceful error handling** — timeouts, connection errors, malformed API responses

---

## 🎯 Quick Start (Railway)

1. **Fork this repo** → Your GitHub account
2. **Go to [railway.app](https://railway.app)** → Create Project → Deploy from GitHub
3. **Add secrets** in Railway Variables (see below)
4. **Done!** Bot starts instantly

---

## 📋 Prerequisites

| Requirement | Why |
|---|---|
| Python 3.12+ | Runtime |
| A Telegram bot token | [@BotFather](https://t.me/BotFather) |
| A VPS provider API token (optional) | For real deployments; use MockProvider for testing |
| GitHub account | For forking and Railway integration |
| Railway account (free tier works) | Cloud hosting |

---

## 🤖 Step 1 — Create the Bot in BotFather

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **HTTP API token** — you'll need it as `TELEGRAM_BOT_TOKEN`.
4. (Optional) Set commands with `/setcommands`:
   ```
   start - Show help and rules
   help - List available commands
   create - Create a new Windows VPS
   status - Show your servers
   reboot - Reboot a server
   delete - Delete a server
   cancel - Cancel current operation
   ```

---

## 🔑 Step 2 — VPS Provider Setup

### For Testing: MockProvider (no real API)

Set `VPS_PROVIDER=mock` in Railway Variables. The bot returns fake data so you can test the full /create → /status → /reboot → /delete flow without spending money.

### For Production: GenericRESTProvider

Set `VPS_PROVIDER=generic` and add these variables in Railway:

| Variable | Example | Description |
|---|---|---|
| `VPS_API_BASE_URL` | `https://api.vultr.com/v2` | Base URL of your VPS provider API |
| `VPS_API_TOKEN` | `abc123def456` | Bearer token for authentication |
| `VPS_PLAN_ID` | `vc2-2c-4gb` | Plan/size ID (check your provider's docs) |
| `VPS_REGION` | `ewr` | Region code (check your provider's docs) |
| `VPS_IMAGE_ID` | `477` | Windows Server image ID |

#### Adapting GenericRESTProvider to Your Provider

Open `bot/services/generic_provider.py` and update:

1. **Endpoint paths** → Change `/servers`, `/servers/{id}`, etc. to match your provider's API
2. **Request body** → The JSON keys in `create_server()` (`label`, `region`, `plan`, `os_id`) must match your provider
3. **Response parsing** → Adjust the `.get()` calls in `_parse_server()` to match the response shape
4. **Password retrieval** → Some providers return the password in the create response; others need a separate reset call

Look for the `╔══ ADAPT THIS ══╗` banner in the code for exact spots to change.

---

## 🔐 Step 3 — Environment Variables

### Railway Setup

1. In your Railway project dashboard, go to **Variables**
2. Add each variable below:

```
TELEGRAM_BOT_TOKEN=<your bot token from BotFather>
ADMIN_USER_IDS=<your Telegram user ID, comma-separated>
VPS_PROVIDER=mock
VPS_API_BASE_URL=
VPS_API_TOKEN=
VPS_PLAN_ID=
VPS_REGION=
VPS_IMAGE_ID=
DATABASE_URL=sqlite:///data/bot.db
ENCRYPTION_KEY=<generate below>
CREATE_RATE_LIMIT_SECONDS=300
MAX_SERVERS_PER_USER=3
WEBHOOK_URL=
PORT=8443
```

### Generate Encryption Key (optional but recommended)

In your terminal:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output into the `ENCRYPTION_KEY` variable in Railway.

### Find Your Telegram User ID

Message [@userinfobot](https://t.me/userinfobot) or [@raw_data_bot](https://t.me/raw_data_bot) and copy your user ID.

---

## 🍴 Step 4 — Fork the Repository

1. Click the **Fork** button on the GitHub repo page.
2. This creates a copy under your GitHub account.

---

## 🚀 Step 5 — Deploy on Railway

### Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub Repo"**.
3. Select your forked repository.
4. Railway auto-builds from `Dockerfile` and starts the bot.

### Monitor the Logs

1. In Railway, click **Deployments** to see build/run logs.
2. If the bot crashes, logs will tell you why (missing env var, API error, etc.).
3. Fix the issue and **redeploy** (Railway can auto-redeploy on every GitHub push).

### Production Notes for Railway

- **Polling is recommended** (leave `WEBHOOK_URL` blank). The bot continuously asks Telegram for new messages — simple, reliable, no public URL needed.
- **Database:** SQLite works, but Railway containers restart frequently. For persistence, add a PostgreSQL plugin (Railway → Add Plugin → PostgreSQL), then Railway will auto-set `DATABASE_URL`.
- **Graceful restarts:** The bot handles `SIGTERM` and stops cleanly.

---

## 🧪 Step 6 — Test Locally (Optional)

```bash
# Create venv
python -m venv .venv && source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Copy env template
cp .env.example .env
# Edit .env with your bot token, user IDs, etc.

# Run the bot
python -m bot.main

# In another terminal, test with your Telegram bot
```

---

## 🧪 Test the Bot (on Railway or Local)

1. Find your bot in Telegram (@your_bot_username)
2. Send `/start` → you should see the welcome message
3. Send `/create` → confirmation buttons appear
4. Click ✅ → the bot provisions a Windows VPS and sends RDP credentials
5. Send `/status` → see your active servers
6. Send `/reboot <SERVER_ID>` → reboot a server
7. Send `/delete <SERVER_ID>` → destroy a server

---

## ❗ Common Railway Issues & Solutions

| Issue | Solution |
|---|---|
| Bot doesn't start / "Missing required environment variable" | Check all env vars in Railway Variables tab; redeploy |
| Bot starts but doesn't respond to /start | Check `TELEGRAM_BOT_TOKEN` is correct; test with [@botname](https://t.me/botname) |
| ⛔ "You are not authorised" | Add your Telegram user ID to `ADMIN_USER_IDS` in Railway Variables |
| "⛔ Server creation is only allowed in private chat" | Message the bot **directly**, not in a group |
| "⏳ Rate limit" | Wait the cooldown period (default 5 minutes) before creating another server |
| Provider create_server fails | Check `VPS_API_BASE_URL`, `VPS_API_TOKEN`, and endpoint paths match your provider |
| Database errors / SQLite locked | Switch to PostgreSQL (Railway → Add Plugin) for better concurrency |
| Bot keeps restarting | Check Railway logs; common causes: invalid token, API unreachable, or wrong provider config |

---

## 🏗 Project Structure

```
├── bot/
│   ├── main.py              # Entry point (webhook or polling)
│   ├── config.py            # All settings from env vars
│   ├── handlers/
│   │   ├── start.py         # /start and /help
│   │   ├── provision.py     # /create and /cancel
│   │   └── status.py        # /status, /reboot, /delete
│   ├── services/
│   │   ├── provider.py      # Abstract VPS provider interface
│   │   ├── mock_provider.py # Fake provider for testing
│   │   ├── generic_provider.py # REST-based real provider
│   │   ├── encryption.py    # Fernet encrypt/decrypt
│   │   ├── rate_limiter.py  # Per-user rate limiting
│   │   └── factory.py       # Provider factory
│   └── db/
│       ├── database.py      # SQLAlchemy models
│       └── repository.py    # DB query helpers
├── tests/                    # Unit tests
├── Dockerfile               # Docker image definition
├── railway.toml             # Railway deployment config
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables
└── README.md               # This file
```

---

## 🔒 Security

- **No hard-coded secrets** — everything reads from environment variables.
- **Private chat only** — RDP credentials are never sent in public/group chats.
- **Ownership isolation** — users only manage their own servers.
- **Rate limiting** — per-user cooldowns prevent abuse.
- **Input sanitisation** — server IDs validated against strict regex.
- **Encrypted storage** — passwords use Fernet (AES-128-CBC). If `ENCRYPTION_KEY` is unset, passwords aren't stored.
- **Audit trail** — every sensitive action logged to the database.
- **Log masking** — passwords and tokens auto-redacted from output.
- **No shell execution** — users cannot run arbitrary commands.
- **Admin-only access** — only `ADMIN_USER_IDS` can perform operations.

---

## ⚠️ Production Checklist

Before going live:

- [ ] Test the full flow (create → status → reboot → delete) with MockProvider
- [ ] Adapt `bot/services/generic_provider.py` for your real VPS provider
- [ ] Generate and set `ENCRYPTION_KEY`
- [ ] Switch `VPS_PROVIDER` from `mock` to `generic`
- [ ] Add `VPS_API_BASE_URL`, `VPS_API_TOKEN`, `VPS_PLAN_ID`, `VPS_REGION`, `VPS_IMAGE_ID`
- [ ] Add a PostgreSQL plugin in Railway for persistent data
- [ ] Monitor Railway logs for errors
- [ ] Share the bot link only with trusted admin users

---

## 📝 License

MIT
