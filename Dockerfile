# ─────────────────────────────────────────────────────────────────────────────
# PenFight Arena — Production Dockerfile
# Runs Daphne (ASGI) so Django Channels WebSockets work correctly.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# System deps needed to compile psycopg2 / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=penfight.settings

WORKDIR /app

# Runtime system libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY . .

# Collect static files at build time (STATIC_ROOT = /app/staticfiles)
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Daphne serves both HTTP and WebSocket (ASGI) on port 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "penfight.asgi:application"]
