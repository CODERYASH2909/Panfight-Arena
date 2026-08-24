# 🖊️ PenFight Arena

**Your Pen. Your Bench. Your Fight.**

A physics-based, multiplayer reimagining of the classic classroom ball-pen fight — built as a real Django + Channels web game with a dark, competitive-gaming UI, cosmetic Pen Skins, Pen Points, ranks, achievements, and both local (hotseat) and online real-time battles.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [What's genuinely complete vs. scaffolded](#whats-genuinely-complete-vs-scaffolded)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Requirements](#requirements)
7. [Installation](#installation)
8. [PostgreSQL Setup](#postgresql-setup)
9. [Environment Variables](#environment-variables)
10. [Database Migration](#database-migration)
11. [Seed Data](#seed-data)
12. [Running the Dev Server](#running-the-dev-server)
13. [Local Multiplayer (Hotseat)](#local-multiplayer-hotseat)
14. [Online Multiplayer](#online-multiplayer)
15. [Admin Setup](#admin-setup)
16. [Game Design Notes](#game-design-notes)
17. [Troubleshooting](#troubleshooting)

---

## Overview

PenFight Arena is a top-down, turn-based physics duel: two pens sit on a classroom bench, players take turns dragging-and-releasing to flick their pen, and the first pen to slide off any edge of the bench loses. It's the desk game every student has played, rebuilt with real momentum, friction, collisions, and knockback — plus a full gaming-platform shell around it: profiles, XP/levels, ranks, a Pen Store, cosmetic skins, achievements, leaderboards, friends, and real-time online battles over WebSockets.

## Features

- **Local Battle** — two players, one device, full hotseat flow with loadout picker, countdown, and victory screen.
- **Online Battle (Private Rooms)** — create a room, share a `PF-XXXX` code, and fight a friend in real time over Django Channels/WebSockets.
- **Quick Match** — a lightweight rating-based matchmaking queue that pairs two searching players automatically.
- **Friend System** — search players, send/accept/decline requests, see friends, challenge them directly.
- **Pen types** — Classic, Heavy, Speed, Precision, Balanced — small, deliberately fair stat differences (never pay-to-win).
- **Pen Skins & Store** — 11 cosmetic skins across Common → Mythic rarity, purchasable with Pen Points, with a featured section.
- **Collection** — track which skins you own out of the total.
- **Pen Points, XP, Levels, Ranks** — Bronze → Grandmaster, all reward math centralized in `rewards/services.py`.
- **Achievements** — First Fight, First Victory, Pen Master, Knockout King, Unstoppable, Pen Legend — auto-checked and rewarded server-side.
- **Leaderboard** — global and friends tabs, highlights your own rank.
- **Match history**, **notifications**, **server-authoritative rewards** (client never decides its own payout).
- **7 arenas** — Classic Classroom, College Classroom, Exam Room, Hostel Table, Computer Lab, Cafeteria Table, Neon Arena.
- **Dark, glassmorphic, neon gaming UI** — no admin-dashboard aesthetic anywhere in the player-facing app.
- **Synthesized SFX** (WebAudio, no binary asset files needed) — flick, collision, fall, countdown, victory/defeat — with an in-battle SFX on/off toggle.

## What's genuinely complete vs. scaffolded

Being upfront about scope, per the build brief:

**Fully working, end to end:**
- Local hotseat battle: aiming, power meter, flick, collision, knockback, falling off the bench, turn switching, countdown, victory screen, server-recorded rewards/XP/achievements.
- Online private-room battle: real WebSocket sync of flicks between two browsers, turn gating, disconnect notice, and **server-authoritative** win resolution + rewards (see `multiplayer/consumers/battle_consumer.py` and `multiplayer/services.py`).
- Full account system: signup/login, profiles, XP/levels, ranks, Pen Points ledger, friends, notifications.
- Pen Store with race-condition-safe, double-purchase-safe buying (`store/services.py`).
- Collection, achievements, leaderboard, match history — all reading real DB state.
- Django admin for every model, with editable prices/feature flags for the store and arenas.

**Deliberately scaffolded / simplified (documented, not hidden):**
- **Physics authority for online play is client-side.** Both peers run the same deterministic physics engine and only relay flick inputs (no gameplay-relevant randomness), which keeps them in sync in practice for a 1v1 casual game — but there's no server-side physics replay/anti-cheat. The **outcome** (who won, all rewards) *is* server-authoritative regardless: the server only trusts a "this pen went off the bench" event as the trigger to look up and finalize the match, and computes every reward itself.
- **Weekly/Monthly leaderboard tabs** currently reuse the same all-time rating table rather than a season-scoped snapshot — a real season system (e.g. a `Season` model + periodic rating resets) is a clean follow-up.
- **Rotating/timed store & tournaments** are not implemented — `PenSkin.is_featured` gives you a "Featured" section admins can toggle, but there's no automatic rotation timer or tournament bracket model. The architecture (separate `multiplayer` app, `Match`/`MatchPlayer` models) is intentionally left open for it.
- **Audio** is synthesized via the WebAudio API rather than shipped `.mp3`/`.wav` files, so the repo has no binary audio assets to manage — this was a deliberate trade for a self-contained, dependency-free zip.
- **Avatars** support image upload but there's no avatar-picker/cosmetic frame system beyond the initial letter-avatar UI.

None of the above blocks the core loop: sign up → customize your pen → fight (locally or online) → win → earn Pen Points/XP → unlock skins → fight again.

## Tech Stack

- **Backend:** Python, Django, Django REST-style function views (no DRF needed — this app doesn't expose a public API)
- **Real-time:** Django Channels + Daphne (ASGI), WebSockets
- **Database:** PostgreSQL (SQLite fallback available for quick trials)
- **Frontend:** Server-rendered Django templates, vanilla TypeScript-flavored ES6 JS (no build step), HTML5 Canvas for the physics engine, hand-written CSS design system (no Tailwind build pipeline — kept dependency-free)
- **Auth:** Django's built-in auth system

## Project Structure

```text
penfight-arena/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
│
├── penfight/                 # project config
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py                # Channels routing lives here
│   └── wsgi.py
│
├── accounts/                  # profiles, XP/rank, friends, notifications, auth views
├── game/                      # pens, skins, arenas, achievements, local battle views
│   └── management/commands/seed_penfight.py
├── rewards/                   # centralized Pen Points/XP ledger + reward service functions
├── store/                     # Pen Store purchase logic
├── multiplayer/                # Match/PrivateRoom/MatchmakingTicket + Channels consumer
│   └── consumers/battle_consumer.py
│
├── templates/                 # all HTML, split by app
├── static/
│   ├── css/main.css           # design system
│   ├── js/engine.js           # physics engine (shared by local + online)
│   ├── js/battle_local.js
│   ├── js/battle_online.js
│   └── js/audio.js            # synthesized SFX
└── media/                      # user-uploaded avatars (created at runtime)
```

## Requirements

- Python 3.10+
- PostgreSQL 13+ (or just set `USE_SQLITE=True` in `.env` to skip this for local testing)
- pip

## Installation

```bash
# 1. Unzip and enter the project
cd penfight-arena

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment config
cp .env.example .env
# edit .env with your own SECRET_KEY and DB credentials
```

## PostgreSQL Setup

```sql
-- in psql
CREATE DATABASE penfight_arena;
CREATE USER penfight WITH PASSWORD 'penfight';
GRANT ALL PRIVILEGES ON DATABASE penfight_arena TO penfight;
```

Then make sure `.env` has matching `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`.

**Don't want to set up Postgres right now?** Set `USE_SQLITE=True` in `.env` and skip straight to migrations — a `db.sqlite3` file will be created automatically.

## Database Migration

Migration files are included for every app. Apply them:

```bash
python manage.py migrate
```

If you change any models, generate a new migration as usual with `python manage.py makemigrations` before `migrate`.

## Seed Data

Populate pens, skins, arenas, and achievements:

```bash
python manage.py seed_penfight
```

Safe to re-run — it uses `update_or_create` throughout, so re-seeding just refreshes values instead of duplicating rows.

## Running the Dev Server

Because `daphne` is registered in `INSTALLED_APPS` (ahead of Django's own app), Django's own `runserver` command is automatically upgraded to run over ASGI — so **one command** serves both regular HTTP pages and the `/ws/battle/<code>/` WebSocket endpoint:

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/**.

Create an account (`/accounts/signup/`) — every new account is auto-granted a Classic Ball Pen, the Classic Blue skin, and 250 starter Pen Points.

## Local Multiplayer (Hotseat)

1. Log in, go to **Play → Local Battle** (`/battle/local/setup/`).
2. Set Player 1 (you) and Player 2's name/pen/skin, pick an arena, hit **Start PenFight**.
3. Pass the device back and forth — the turn banner tells you whose turn it is. Drag your pen backward on the canvas and release to flick; the further you drag, the harder the flick.
4. First pen to slide off the bench loses. Only the logged-in Player 1 slot's account receives Pen Points/XP/rank changes (Player 2 may be a guest with no account).

## Online Multiplayer

Two options:

**Private Room**
1. Player A: Dashboard → **Private Room** → creates a room, gets a code like `PF-8X92`.
2. Player B: Dashboard → **Join Room**, enters the code.
3. Host picks the arena and clicks **Start PenFight**; both players are redirected into the same live battle screen.

**Quick Match**
1. Dashboard → **Quick Match** → **Search for Opponent**.
2. The client polls every 2s; once another searching player is within rating range, both are paired into a fresh room automatically and redirected in.

**Friend Challenge**
- From Friends or a friend's profile, click **Challenge** — this creates a ready-to-start private room and sends them a notification with a direct link.

Under the hood, both players' browsers open a WebSocket to `/ws/battle/<room-code>/`. Flicks are relayed and replayed identically on both screens (see [scaffolding notes](#whats-genuinely-complete-vs-scaffolded) above); the moment either screen detects a pen has gone off the bench, it reports that to the server, which is the **only** place that finalizes the winner and grants rewards.

> Running more than one dev server process (e.g. behind gunicorn/multiple workers) requires a real channel layer — set `USE_REDIS_CHANNEL_LAYER=True` and a running Redis instance in `.env`. A single `runserver` process works fine with the default in-memory layer.

## Admin Setup

```bash
python manage.py createsuperuser
```

Then visit `/admin/` to:
- Add/edit Pens, Pen Skins (price, rarity, featured flag, purchasable toggle)
- Add/edit Arenas (colors, unlock level, active toggle)
- Configure Achievements (target stat/value, PP/XP rewards)
- Inspect Matches, Pen Point transactions, Store purchases, and Notifications

## Game Design Notes

- **Fairness:** Pen stat spreads (mass/power/friction/control) are intentionally small — see `game/management/commands/seed_penfight.py`. Skins never touch gameplay stats, only rendering (`body_color`, `accent_color`, `trail_color`, `glow`, `pattern`).
- **Reward centralization:** every Pen Points/XP grant in the entire codebase funnels through `rewards/services.py` (`grant_pen_points`, `grant_xp`, `apply_match_result_rewards`, `check_achievements`). Nothing computes reward numbers inline elsewhere — this was a specific project requirement to avoid drift/duplication.
- **Server authority:** `store/services.py::purchase_skin` and `multiplayer/services.py::finish_online_match` are both wrapped in `transaction.atomic` and are the *only* code paths allowed to mutate Pen Points/inventory/match results, specifically to prevent duplicate-purchase and duplicate-reward race conditions.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `django.db.utils.OperationalError` on startup | Postgres isn't running/reachable, or `.env` credentials are wrong. Try `USE_SQLITE=True` to isolate the issue. |
| WebSocket won't connect / online battle stuck on "Connecting..." | Make sure you started the server with `python manage.py runserver` (not a plain WSGI server) and that `daphne` is first in `INSTALLED_APPS`. Check the browser console for the exact WS error. |
| Static files (CSS/JS) missing in DEBUG mode | Confirm `STATICFILES_DIRS` points at the repo's `static/` folder and you haven't accidentally run `collectstatic` into a stale `staticfiles/` that's shadowing it. |
| New user has no starter pen/skin | The `accounts.signals` → `game.services.grant_starter_kit` flow requires the DB to already contain a Pen with `kind="classic"` and a `PenSkin` with `is_starter=True` — run `python manage.py seed_penfight` **before** creating accounts. |
| Achievements never unlock | `rewards.services.check_achievements` compares `Achievement.target_stat` against a `Profile` field name — if you add a custom achievement, make sure `target_stat` is a real, comparable Profile field (e.g. `wins`, `knockouts`, `best_win_streak`, `rating`, `matches_played`). |
| Two local dev servers don't see each other's Quick Match tickets | Each `runserver` process has its own in-memory channel layer *and* its own DB connection is fine (DB is shared), but if you're running Channels workers separately for testing, make sure `USE_REDIS_CHANNEL_LAYER=True` so all processes share one channel layer. |

---

Built with Django + Channels. No pay-to-win, ever. 🖊️⚔️
