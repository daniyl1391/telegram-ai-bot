FROM python:3.12-slim

LABEL maintainer="your-email@example.com"
LABEL description="Telegram bot that provisions Windows VPS instances"

# Don't write .pyc files & flush stdout immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data dir for SQLite (if used)
RUN mkdir -p /app/data

# Railway doesn't require healthcheck for background workers
# But we can add one for webhook mode if needed
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8443}/health 2>/dev/null || exit 1

EXPOSE ${PORT:-8443}

# Run the bot
CMD ["python", "-m", "bot.main"]
