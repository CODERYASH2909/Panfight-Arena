"""
PenFight Arena — Django settings.

Environment-driven configuration. Copy `.env.example` to `.env` and adjust
values for your machine before running the server.

Production deployment:
  - Database  → Supabase PostgreSQL (set DATABASE_URL env var)
  - WebSocket → Railway (Daphne/ASGI), Redis channel layer
  - Storage   → Supabase Storage (optional, set SUPABASE_URL + SUPABASE_KEY)
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
# Local project settings should take precedence over inherited shell values.
# This keeps DEBUG=True in .env effective when running the development server.
environ.Env.read_env(BASE_DIR / ".env", overwrite=True)

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-secret-key-change-me-in-prod")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "testserver"])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",

    "accounts",
    "game",
    "rewards",
    "store",
    "multiplayer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serves staticfiles in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "penfight.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "penfight.wsgi.application"
ASGI_APPLICATION = "penfight.asgi.application"

# ---------------------------------------------------------------------------
# Database — Priority order:
#   1. DATABASE_URL env var (Supabase connection string — production)
#   2. Individual DB_* vars (local Postgres)
#   3. SQLite (USE_SQLITE=True in .env — quick local dev, no Postgres needed)
# ---------------------------------------------------------------------------
_database_url = env("DATABASE_URL", default="")

if _database_url:
    # Supabase / Railway / any Postgres connection string
    # django-environ parses postgres:// and postgresql:// correctly.
    DATABASES = {
        "default": env.db_url("DATABASE_URL")
    }
    # Supabase transaction pooler (port 6543) requires disable_server_side_cursors
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
elif env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="penfight_arena"),
            "USER": env("DB_USER", default="penfight"),
            "PASSWORD": env("DB_PASSWORD", default="penfight"),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }

# ---------------------------------------------------------------------------
# Channels — real-time layer for online PenFight battles.
# Uses Redis in production; falls back to the in-memory layer for local/dev
# use (single-process only — fine for local testing, not for production).
# ---------------------------------------------------------------------------
if env.bool("USE_REDIS_CHANNEL_LAYER", default=False):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [env("REDIS_URL", default="redis://127.0.0.1:6379/0")]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise compressed static file storage for production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "game:landing"

# CSRF / security niceties for local dev over plain HTTP.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1:8000", "http://localhost:8000"],
)

# ---------------------------------------------------------------------------
# Production security settings — only active when DEBUG=False
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Supabase Storage (optional — replaces local filesystem for avatar uploads).
# If SUPABASE_URL is set, configure django-storages to use Supabase's
# S3-compatible API. Requires: pip install django-storages boto3
# ---------------------------------------------------------------------------
SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_KEY = env("SUPABASE_KEY", default="")
SUPABASE_BUCKET = env("SUPABASE_BUCKET", default="penfight-avatars")

# ---------------------------------------------------------------------------
# PenFight Arena game-balance constants — centralised so reward numbers are
# never duplicated/hand-typed elsewhere in the codebase.
# ---------------------------------------------------------------------------
PENFIGHT_REWARDS = {
    "MATCH_WIN_PP": 100,
    "MATCH_LOSS_PP": 25,
    "WIN_STREAK_BONUS_PP": 50,
    "WIN_STREAK_THRESHOLD": 3,
    "DAILY_LOGIN_PP": 25,
    "TOURNAMENT_WIN_PP": 500,
    "MATCH_WIN_XP": 120,
    "MATCH_LOSS_XP": 40,
}
