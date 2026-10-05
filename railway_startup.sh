#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# railway_startup.sh
# Runs once on every Railway deploy before Daphne starts.
# Handles DB migrations, superuser creation, and initial game data seeding.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "🏟️  PenFight Arena — Railway Startup"
echo "========================================"

# ── 1. Run DB migrations ──────────────────────────────────────────────────────
echo "▶  Running database migrations..."
python manage.py migrate --noinput
echo "✅ Migrations complete."

# ── 2. Create Django superuser (idempotent — skips if already exists) ─────────
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "▶  Ensuring superuser '$DJANGO_SUPERUSER_USERNAME' exists..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('  Created superuser.')
else:
    print('  Superuser already exists — skipped.')
"
fi

# ── 3. Seed initial game data (idempotent fixtures) ───────────────────────────
echo "▶  Seeding game fixtures (pens, skins, arenas, achievements)..."
python manage.py seed_penfight || echo "  Seed failed or skipped."

# ── 4. Start Daphne (ASGI — HTTP + WebSocket) ─────────────────────────────────
echo ""
echo "🚀 Starting Daphne on 0.0.0.0:${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" penfight.asgi:application
