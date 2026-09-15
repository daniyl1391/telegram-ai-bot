FROM python:3.12-slim

# PYTHONUNBUFFERED matters on Railway: without it the log pane looks empty.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# All dependencies ship as wheels, so no compiler is needed (the old image
# installed gcc for nothing).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Writable mount point for the SQLite database. On Railway attach a Volume here
# so data survives redeploys.
RUN mkdir -p /data && \
    adduser --disabled-password --gecos "" --uid 10001 botuser && \
    chown -R botuser:botuser /app /data
USER botuser

ENV DATA_DIR=/data

CMD ["python", "-u", "main.py"]
