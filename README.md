# 🤖 Telegram AI Bot

A commercial-grade Telegram AI bot: multi-model AI chat, a complete in-Telegram
admin panel, a shop with card-to-card payments and manual approval, subscription
quotas, a support ticket system, and a fully bilingual 🇮🇷 Persian / 🇬🇧 English
interface.

**Only two environment variables.** Everything else (AI models, API keys, prices,
card number, quotas, rate limits) is configured from the admin panel inside
Telegram.

---

## 🚀 Quick start

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in the two values
python main.py
```

Then in Telegram: send `/start` to your bot, pick a language, send `/admin`, open
**🤖 AI Models → ➕ Add model**, and you are live.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_USER_IDS` | ✅ | Your numeric Telegram ID from [@userinfobot](https://t.me/userinfobot). Comma-separate multiple admins. |
| `DATA_DIR` | ➖ | Where the SQLite file lives. Defaults to `/data`, falls back to `./data`. |
| `LOG_LEVEL` | ➖ | `INFO` by default. |

The bot refuses to start with a clear message if either required variable is
missing or malformed, instead of crashing on an opaque `InvalidToken`.

---

## 🚄 Deploy on Railway

1. Push this repository to GitHub.
2. On Railway: **New Project → Deploy from GitHub repo**.
3. **Variables** → add `TELEGRAM_BOT_TOKEN` and `ADMIN_USER_IDS`.
4. **⚠️ Add a Volume mounted at `/data`.** Without it the SQLite database is wiped
   on every redeploy and you lose all users, payments and settings.
5. Keep **replicas at 1**. Long polling allows exactly one instance; two would
   fight over `getUpdates` and Telegram would return
   `Conflict: terminated by other getUpdates request`.

`railway.toml`, `Dockerfile` and `Procfile` are all included and consistent.

---

## ✨ Features

### 🤖 AI
- Chat with the AI by simply typing in the bot.
- **Fast progressive streaming**: compatible providers stream tokens and the bot
  edits one Telegram message at a controlled interval, with an automatic JSON
  fallback when a provider does not support streaming.
- **Multimodal input**: send a photo with a caption, PDF, DOCX, TXT, CSV, JSON or
  code file and the bot downloads it safely, extracts text or sends an image data
  URL to a vision-capable model. Receipt photos remain in the payment-review flow.
- **Multi-model**: add as many providers as you want from the panel. A paid plan
  can be restricted to selected model IDs/names, or allowed to use all models.
- **OpenAI-compatible** request format, so OpenAI, OpenRouter, Groq, Together,
  DeepSeek, Azure and most proxies work out of the box. Replies are also parsed
  from Anthropic-native, Gemini-native and simple custom shapes.
- **Multi-API-key** per model: comma-separate several keys and the bot rotates to
  the next one when a key is rejected.
- Retry with exponential backoff on timeouts, connection errors and 429/5xx.
- Per-user conversation memory, with a configurable depth and a clear button.
- **Usage metering**: provider usage metadata is stored when available; otherwise
  a conservative estimate is shown. Subscriptions can charge by messages, tokens,
  or whichever quota is exhausted first.
- A user is **never charged for a failed request**.

### 👑 Admin panel (`/admin`)
| Section | What you can do |
|---|---|
| 👥 Users | Paginated list, search by ID/username, per-user detail, change message quota, configure token quota/model policy, grant a plan, DM a user, ban / unban |
| 🤖 AI Models | Add, edit name / API URL / API key / model ID, **test connection**, set default, enable/disable, delete |
| 🛒 Shop | Create products with price, duration and message count; edit any field; enable/disable; delete |
| 💳 Payments | Pending queue, receipt view, one-tap **approve / reject**, set card number and card holder, toggle the online gateway |
| 🎫 Tickets | Open ticket list, full conversation view, reply to the user, close |
| 📊 Stats | Users, new today, active subscriptions, AI messages, confirmed revenue, pending payments, open tickets |
| ⚙️ Settings | Free message/token quota, quota mode, rate limit, stream speed, output limit, file size, history, system prompt, model scope, shop/support toggles |
| 📢 Broadcast | Send a message to every non-banned user |

### 🧮 Quota and plan policy
- Each product can define message quota, token quota, duration, and an allowed
  model scope (`all` or comma-separated model names/IDs).
- Admins can grant the same product to a user without a payment.
- Usage is recorded in `ai_usage` with prompt/completion/total tokens, latency and
  input type (`text`/`image`). The account screen shows token consumption.

### 💳 Payments
Card-to-card with manual approval: the user picks a product, sees your card
number, sends a receipt photo or reference number, and every admin instantly gets
a notification with **✅ Confirm / ❌ Reject** buttons. Approving activates the
plan atomically and notifies the buyer. An optional online-gateway hook is
included behind a toggle.

### 🌍 Bilingual
Every button, message, error and admin screen exists in both Persian and English
(183 strings, no gaps, enforced by the test suite). Users pick a language on
first contact and can switch any time from the menu or `/language`.

### 🔐 Security
- Admin rights come **only** from `ADMIN_USER_IDS`. A database flag cannot mint an
  admin.
- Every admin callback is re-checked, so replaying a leaked `callback_data` string
  gets a non-admin nowhere.
- API keys are masked on screen (`sk-p••••••••3456`) and never printed in full.
- Sliding-window rate limiting and duplicate-message anti-spam (admins exempt).
- Validation on every input: numbers with ranges, URLs, 16-digit cards, text
  lengths. Persian digits (`۱۲۳۴`) are accepted everywhere.
- All user text is HTML-escaped before rendering.
- The container runs as a non-root user.

---

## 🗂 Project structure

```
main.py                    entry point + the full handler registry
bot/
├── config.py              env validation, data paths, seeded defaults
├── database.py            SQLite layer, transactions, migrations
├── i18n.py                Persian / English string catalogue
├── keyboards.py           every inline keyboard
├── security.py            admin guard, rate limit, anti-spam, validation
├── handlers/
│   ├── common.py          language, safe edit, the FSM
│   ├── router.py          the single text/photo entry point
│   ├── start.py           /start, language, account, navigation
│   ├── ai_chat.py         AI conversation
│   ├── shop.py            shop + checkout + receipts
│   ├── support.py         tickets
│   ├── admin.py           the admin panel
│   └── errors.py          global error handler
├── services/
│   ├── ai_manager.py      streaming provider client, retries, key rotation, usage
│   ├── payment.py         atomic approval flow
│   └── subscription.py    message/token quotas and model policy
├── media.py               safe photo/PDF/DOCX/text attachment pipeline
└── admin/panel.py         privileged write operations
tests.py                   65 tests
tests_stubs/               offline stand-ins used only by tests.py
```

---

## 🧪 Tests

```bash
python tests.py
```

65 tests, all passing. They run without network access and without a bot token:
if `python-telegram-bot` / `aiohttp` are missing, lightweight stubs from
`tests_stubs/` are used instead.

Coverage highlights:
- **No dead buttons**: every `callback_data` produced by any keyboard is matched
  against the registered handler patterns. A dead button fails the suite.
- Database: atomic nested writes, rollback, newest-row ordering, timezone-aware
  timestamps, in-place migration of a database made by the previous version.
- Full purchase flow: order → receipt → admin notification → approval → active
  plan, plus double-approval prevention.
- Security: admin guard, callback replay, permission checks, key masking, rate
  limit, anti-spam, validation, HTML escaping, banned users.
- AI client: exact request shape, nine response shapes, retry on 429, key
  rotation on 401, timeout handling, no stale model cache.
- Handler smoke tests for every user screen and every admin screen, in both
  languages.

> Note: the suite covers all bot-side logic. It deliberately does not call the
> real Telegram API or a real AI provider, so you still need to add one working
> model and send one live message to confirm your own credentials.

---

## 🔧 Adding an AI model

`/admin` → **🤖 AI Models** → **➕ Add model**, then send four values in turn:

| Step | Example |
|---|---|
| Name | `GPT-4o` |
| API URL | `https://api.openai.com/v1/chat/completions` |
| API key | `sk-...` (or `sk-key1, sk-key2` to rotate) |
| Model ID | `gpt-4o-mini` |

Then tap **🧪 Test connection** to confirm it works before users hit it.

Other providers:
- OpenRouter — `https://openrouter.ai/api/v1/chat/completions`
- Groq — `https://api.groq.com/openai/v1/chat/completions`
- DeepSeek — `https://api.deepseek.com/chat/completions`

---

## 📄 License

MIT
