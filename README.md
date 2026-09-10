# PenFight Arena

> Your pen. Your bench. Your fight.

PenFight Arena is a multiplayer, turn-based physics game inspired by the classic classroom pen fight. Choose a pen, aim your flick, and knock your opponent off the bench. The project combines a Django web application with real-time battles, player progression, cosmetic rewards, and a dark gaming-focused interface.

## Highlights

- **Local battle** — two-player hotseat matches on one device.
- **Online battle** — private rooms, friend challenges, and quick matchmaking.
- **Physics gameplay** — aim by dragging your pen backwards and releasing to flick it.
- **Progression** — earn Pen Points, XP, levels, ranks, achievements, and match history.
- **Cosmetics** — collect pens and skins without pay-to-win gameplay advantages.
- **Social features** — accounts, profiles, friends, notifications, and leaderboards.
- **Admin tools** — manage content, arenas, skins, achievements, and player data through Django Admin.

## Quick start

The fastest way to run the project locally is with SQLite. You only need Python and pip.

### 1. Create and activate a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows PowerShell
py -m venv venv
.\\venv\\Scripts\\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

Copy the example settings file and use SQLite for a zero-setup local database.

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Ensure your `.env` contains:

```env
USE_SQLITE=True
DEBUG=True
```

### 4. Prepare game data and database

```bash
python manage.py migrate
python manage.py seed_penfight
```

`seed_penfight` creates or refreshes the default pens, skins, arenas, and achievements. It is safe to run more than once.

### 5. Start the server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser. Create an account to receive the starter pen, starter skin, and Pen Points.

## How to play

### Local battle

1. Sign in and choose **Play → Local Battle**.
2. Set each player's name, pen, skin, and arena.
3. Drag your pen backwards, then release to flick it forward.
4. Take turns until one pen falls off the bench.

The signed-in first player receives the match rewards; the second player can be a guest.

### Online battle

Choose one of these from the dashboard:

- **Private Room:** create a room, share its `PF-XXXX` code, then start when your opponent joins.
- **Quick Match:** enter the matchmaking queue and the app pairs nearby ratings automatically.
- **Friend Challenge:** send a direct challenge from a friend's profile or the Friends page.

Online matches use WebSockets at `/ws/battle/<room-code>/`. The regular `runserver` command runs through Daphne/ASGI, so one local server supports both web pages and WebSockets.

## Technology

| Area | Used in this project |
| --- | --- |
| Backend | Python, Django |
| Real-time | Django Channels, Daphne, WebSockets |
| Database | PostgreSQL, with SQLite for local development |
| Frontend | Django templates, vanilla JavaScript, HTML Canvas, CSS |
| Media | Pillow for uploaded avatars |

## Project layout

```text
penfight-arena/
├── manage.py                 # Django commands
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── penfight/                 # Django settings, URLs, ASGI entry point
├── accounts/                 # Authentication, profiles, friends, notifications
├── game/                     # Pens, skins, arenas, achievements, local battles
├── multiplayer/              # Rooms, matchmaking, matches, WebSocket consumer
├── rewards/                  # Pen Points, XP, ranks, and reward rules
├── store/                    # Cosmetic store and purchase logic
├── templates/                # Server-rendered HTML
└── static/                   # CSS, game engine, battle scripts, audio
```

Useful files:

- `static/js/engine.js` — shared browser physics engine.
- `multiplayer/consumers/battle_consumer.py` — live battle WebSocket handling.
- `multiplayer/services.py` — server-side online match completion and rewards.
- `rewards/services.py` — centralized Pen Point and XP reward logic.
- `game/management/commands/seed_penfight.py` — default game-content seed command.

## Configuration

All settings are read from `.env`. Start with `.env.example`.

| Variable | Purpose | Local recommendation |
| --- | --- | --- |
| `SECRET_KEY` | Django cryptographic key | Use a unique secret outside local development |
| `DEBUG` | Enables Django debug mode | `True` locally; `False` in production |
| `ALLOWED_HOSTS` | Hosts Django accepts | `127.0.0.1,localhost` locally |
| `USE_SQLITE` | Uses SQLite instead of PostgreSQL | `True` for a quick start |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection settings | Required when `USE_SQLITE=False` |
| `USE_REDIS_CHANNEL_LAYER` | Shares Channels messages across processes | `False` locally; `True` for multi-process deployment |
| `REDIS_URL` | Redis connection URL | Required when Redis channel layer is enabled |
| `CSRF_TRUSTED_ORIGINS` | Allowed browser origins for CSRF requests | Add your deployed HTTPS domain |

## PostgreSQL and Redis setup

SQLite is ideal for trying the game locally. For a production-like configuration, create a PostgreSQL database and set `USE_SQLITE=False`.

```sql
CREATE DATABASE penfight_arena;
CREATE USER penfight WITH PASSWORD 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE penfight_arena TO penfight;
```

Set the matching `DB_*` variables in `.env`, then run migrations again:

```bash
python manage.py migrate
python manage.py seed_penfight
```

For multiple server processes, enable Redis:

```env
USE_REDIS_CHANNEL_LAYER=True
REDIS_URL=redis://127.0.0.1:6379/0
```

The default in-memory channel layer is suitable only for a single local server process.

## Admin

Create an administrator account:

```bash
python manage.py createsuperuser
```

Then visit [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) to manage:

- pens, skins, prices, rarity, and featured items;
- arenas and unlock requirements;
- achievements and their rewards;
- matches, purchases, Pen Point transactions, and notifications.

## Game rules and implementation notes

- The first pen to leave the bench loses.
- Pen types have intentionally small stat differences. Skins are cosmetic and do not affect stats.
- Pen Points, XP, inventory updates, and match rewards are calculated on the server to avoid client-controlled payouts.
- Store purchases and online match completion use database transactions to prevent duplicate purchases or rewards.
- Online clients exchange flick inputs and replay the shared deterministic physics in the browser. The server finalizes the reported match result and rewards, but it does not run a server-side physics replay or anti-cheat simulation.
- Weekly and monthly leaderboard views currently reuse the all-time rating data; seasonal snapshots are not yet implemented.
- The featured store is admin-controlled rather than automatically rotating, and tournaments are not yet implemented.

## Common commands

```bash
# Apply migrations
python manage.py migrate

# Generate migrations after changing models
python manage.py makemigrations

# Populate or refresh game content
python manage.py seed_penfight

# Run development server (HTTP + WebSockets)
python manage.py runserver

# Create an admin user
python manage.py createsuperuser

# Run Django diagnostics
python manage.py check
```

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Database connection error | Set `USE_SQLITE=True` for local testing, or confirm PostgreSQL is running and all `DB_*` values are correct. |
| New accounts have no starter items | Run `python manage.py seed_penfight` before creating the accounts. |
| Online battle stays on “Connecting” | Use `python manage.py runserver`, not a WSGI-only server. Also check the browser console for the WebSocket error. |
| Two server processes cannot share live updates | Run Redis and set `USE_REDIS_CHANNEL_LAYER=True`. |
| CSS or JavaScript is missing in development | Confirm the server is in debug mode and that `static/` exists in the project root. |
| Port 8000 is already in use | Run `python manage.py runserver 8001` and open `http://127.0.0.1:8001/`. |

## Contributing

Before opening a change, run the project checks and test the relevant player flow:

```bash
python manage.py check
```

When changing data models, include the generated migration. When changing game balance or rewards, keep the logic centralized in the relevant services rather than duplicating values in views or JavaScript.

---

Built with Django and Django Channels.
