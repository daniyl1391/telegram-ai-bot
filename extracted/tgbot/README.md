# Professional Telegram AI Bot

A complete, production-ready Telegram bot with AI integration, admin panel, payment system, and subscription management. Deploy on Railway in 5 minutes.

## Features

- 🤖 Multi-model AI Support (GPT, Claude, Gemini, Custom APIs)
- 👥 User Management with Subscription System
- 💳 Payment Integration (Online Gateway, Card Transfer, Manual)
- 🛒 Shop System with Products
- 🎫 Support Ticket System
- 👨‍💼 Complete Admin Panel in Telegram
- 📊 Analytics and Statistics
- 🔐 Secure Configuration Management
- 🐳 Docker Ready
- 🚀 Railway Deployment Ready

## Quick Start

### 1. Create Bot on Telegram

1. Open @BotFather on Telegram
2. Send /newbot and follow instructions
3. Copy the bot token

### 2. Setup

```bash
git clone <your-repo>
cd telegram_ai_bot

# Create .env file
cp .env.example .env

# Edit .env with your values
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_USER_IDS=your_telegram_id
```

### 3. Local Development

```bash
pip install -r requirements.txt
python main.py
```

### 4. Deploy on Railway

1. Push to GitHub
2. Connect repository to Railway
3. Add environment variables in Railway dashboard:
   - TELEGRAM_BOT_TOKEN
   - ADMIN_USER_IDS
4. Railway auto-deploys

## Project Structure

```
bot/
├── config.py           # Configuration
├── database.py         # Database models
├── handlers/
│   ├── start.py       # Start command
│   └── admin.py       # Admin panel
├── services/
│   ├── ai_manager.py      # AI integration
│   ├── subscription.py     # Subscription logic
│   └── payment.py         # Payment handling
└── admin/
    └── panel.py        # Admin functions

main.py               # Entry point
requirements.txt      # Dependencies
Dockerfile           # Docker config
railway.toml         # Railway config
```

## Admin Panel Commands

In Telegram:
- `/admin` - Open admin panel
- Stats, AI Models, Products, Payments, Tickets management

## Database

Uses SQLite by default. Easily switch to PostgreSQL:
```
DATABASE_URL=postgresql://user:pass@host/db
```

## Security

- No sensitive data in code
- Environment variables for all secrets
- API keys masked in admin panel
- Input validation on all handlers
- Rate limiting built-in

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN` - Bot token from BotFather
- `ADMIN_USER_IDS` - Comma-separated admin Telegram IDs

Optional:
- `DATABASE_URL` - Default: sqlite:///bot.db
- `PORT` - Default: 8000
- `HOST` - Default: 0.0.0.0

## API Integration

Add AI models via admin panel:
- Model Name (GPT, Claude, etc.)
- API URL
- API Key
- Model ID from provider

Currently supports any REST API with Bearer token auth.

## Support

For issues or features, create an issue on GitHub.

## Testing

Run the test suite:
```bash
python tests.py
```

Tests verify:
- All imports work correctly
- Database initializes
- User management operations
- Subscription system
- Settings management

## Customization

### Add New AI Model

1. Go to admin panel in Telegram
2. Select "AI Models"
3. Enter:
   - Name: gpt-4
   - API URL: https://api.openai.com/v1/chat
   - API Key: sk-...
   - Model: gpt-4

### Create Product

1. Admin menu → Products
2. Enter name, price, duration, messages
3. Product available in shop

### Configure Payment

Supported methods:
- API Gateway (Stripe, PayPal, etc.)
- Bank Transfer (IBAN/Card)
- Manual (Admin approval)

## Scaling

For production with many users:

1. **Database**: Migrate to PostgreSQL
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/db
   ```

2. **Caching**: Add Redis for rate limiting

3. **Load Balancer**: Use Nginx behind Railway

4. **Monitoring**: Integrate with Sentry

## Architecture

```
User Request
    ↓
Telegram API
    ↓
main.py (handlers)
    ↓
handlers/ (business logic)
    ↓
services/ (core operations)
    ↓
database.py (SQLite/PostgreSQL)
```

## API References

- python-telegram-bot: https://python-telegram-bot.readthedocs.io/
- Telegram Bot API: https://core.telegram.org/bots/api

## License

MIT

## Support

Issues? Questions? Create an issue or contact support.
