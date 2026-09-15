# 🚀 Railway Deployment Guide

This guide walks you through deploying the Telegram VPS Bot to Railway.

---

## Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app, free tier is fine)
- Telegram bot token (from @BotFather)
- Your Telegram user ID (from @userinfobot)

---

## Step 1: Fork the Repository

1. Go to the GitHub repo and click **Fork**
2. This creates a copy under your GitHub account

---

## Step 2: Create a Railway Project

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **"New Project"** → **"Deploy from GitHub Repo"**
4. Select your forked `telegram-vps-bot` repository
5. Railway auto-detects `Dockerfile` and starts building
6. Wait for the build to finish (usually ~2 mins)

---

## Step 3: Add Environment Variables

Once deployed, configure secrets:

1. In Railway dashboard, click your project
2. Go to **Variables** tab
3. Add each variable **exactly as shown**:

### Required Variables

```
TELEGRAM_BOT_TOKEN = 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ADMIN_USER_IDS = 987654321,111222333
```

> **Find your Telegram user ID:** Message @userinfobot and copy the number

### Provider Configuration

For testing (no real API costs):
```
VPS_PROVIDER = mock
```

For production with a real provider:
```
VPS_PROVIDER = generic
VPS_API_BASE_URL = https://api.your-provider.com/v1
VPS_API_TOKEN = your-api-key-here
VPS_PLAN_ID = plan-id-from-provider
VPS_REGION = region-code-from-provider
VPS_IMAGE_ID = windows-image-id
```

### Optional but Recommended

```
ENCRYPTION_KEY = <generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
CREATE_RATE_LIMIT_SECONDS = 300
MAX_SERVERS_PER_USER = 3
```

### For Production (Persistent Database)

1. In Railway, click **Add Plugin** → Select **PostgreSQL**
2. Railway auto-populates `DATABASE_URL`
3. That's it — data now persists across restarts

---

## Step 4: Deploy

After adding all variables:

1. Click **Redeploy** in Railway dashboard
2. Check **Deployments** tab for build logs
3. Once green ✅, the bot is live!

---

## Step 5: Test

1. Find your bot in Telegram (or go to @BotFather, find it in /mybots)
2. Send `/start` → should see a welcome message
3. Send `/create` → confirm to provision a test VPS
4. You should receive RDP credentials (fake if using MockProvider)

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Build fails | Check Railway logs; usually missing env vars. Add them and redeploy. |
| Bot doesn't respond | Verify `TELEGRAM_BOT_TOKEN` is correct. Test with @botname in Telegram. |
| "Not authorised" error | Make sure your Telegram user ID is in `ADMIN_USER_IDS`. |
| "Provisioning timed out" | Increase timeout or check provider API is reachable. |
| Database full / SQLite locked | Add PostgreSQL plugin for better concurrency. |

---

## Auto-Redeploy on GitHub Changes

Railway watches your GitHub repo. When you push changes:

1. Railway automatically rebuilds the Docker image
2. Restarts the bot with new code
3. Useful for quick fixes and updates

---

## Viewing Logs

1. In Railway, go to **Deployments**
2. Click the latest deployment
3. Scroll to see live logs
4. Grep for "ERROR" or "WARNING" to spot issues

---

## Stopping / Removing the Bot

1. In Railway, go to **Settings**
2. Click **Remove**
3. This stops the bot and deletes it from Railway

---

That's it! 🎉 Your bot is now running 24/7 on Railway.
