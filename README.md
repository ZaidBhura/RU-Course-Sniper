# RU Course Sniper

Monitors Rutgers course availability and sends instant notifications when a watched section opens up.

> **This tool does not automate enrollment.** It only detects when a seat opens and notifies you — you still need to manually enroll in WebReg.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind v4, shadcn/ui |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2 |
| Worker | Celery + Redis |
| Database | PostgreSQL 16 |
| Auth | JWT with httpOnly cookies |

---

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker
- `make`

---

## First-Time Setup

```bash
git clone <repo>
cd RU-Course-Sniper

make setup
```

Then copy the example env file and fill in your values:

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in the required fields (see Environment Variables below).

---

## Running Locally

```bash
make dev
```

This starts Postgres + Redis in Docker, the backend API, the frontend, and the Celery worker — all at once. Hit `Ctrl-C` to stop everything.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/api/docs |

### Run services individually

```bash
make infra          # Postgres + Redis only
make dev-backend    # backend API only
make dev-frontend   # frontend only
make dev-worker     # Celery worker + scheduler only
make infra-down     # stop Postgres + Redis
```

---

## How It Works

1. **Polling** — The worker polls the Rutgers SOC API every 10 seconds. One poll covers all users — not one poll per user.

2. **Detection** — The worker compares the current open sections against the previous poll and detects what just opened or closed.

3. **Immediate notify on add** — If you add a course that's already open, you get notified right away without waiting for the next poll.

4. **Notification** — When a match is found, a notification is sent via Discord webhook or Pushover. A dedup key in Redis prevents double-sending for the same open event.

5. **Opened tab** — After you're notified, the course moves from your Watching tab to your Opened tab with a direct WebReg enrollment link.

6. **Resnipe** — If you miss the seat or want to watch again, hit Resnipe on any course in the Opened tab and it moves back to Watching.

7. **Re-notification** — When a course closes and reopens, you get notified again automatically.

8. **Course enrichment** — Course names, instructors, and meeting times are fetched from the SOC API every 10 minutes and shown in notifications and the UI.

---

## Environment Variables

Required fields in `backend/.env`:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection URL (async driver: `postgresql+asyncpg://...`) |
| `SYNC_DATABASE_URL` | Postgres connection URL (sync driver: `postgresql+psycopg2://...`) |
| `REDIS_URL` | Redis connection URL |
| `SECRET_KEY` | Random secret used to sign JWTs — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `FERNET_KEY` | Encryption key for stored notification credentials — generate with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

Optional:

| Variable | Description |
|---|---|
| `ENVIRONMENT` | `development` / `production` (default: `development`) |
| `SENTRY_DSN` | Sentry DSN for error tracking (leave blank to disable) |
| `POLL_INTERVAL_SECONDS` | How often to poll the SOC API (default: 10, minimum: 10) |

---

## Testing

```bash
make test           # run everything
make test-backend   # pytest only
make test-frontend  # vitest only
```

The backend test suite uses a separate `course_sniper_test` database. Make sure `make infra` is running before running backend tests.

### Individual pytest options

```bash
cd backend
.venv/bin/pytest -v                     # verbose
.venv/bin/pytest tests/test_auth.py -v  # single file
.venv/bin/pytest -k "isolation" -v      # by keyword
```

### End-to-end tests (Playwright)

Requires the full stack running in another terminal:

```bash
cd frontend
npm run test:e2e
npm run test:e2e:ui   # interactive mode
```

---

## Linting & Type Checking

```bash
make lint           # run everything
make lint-backend   # ruff + mypy
make lint-frontend  # eslint + tsc
```

---

## Database Migrations

```bash
cd backend
.venv/bin/alembic upgrade head                              # apply all migrations
.venv/bin/alembic downgrade -1                              # roll back one
.venv/bin/alembic revision --autogenerate -m "description"  # create new migration
```

---

## Project Structure

```
RU-Course-Sniper/
├── Makefile
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── api/          # Auth + DB session dependencies
│   │   ├── core/         # Config, security, logging
│   │   ├── db/           # Database engine + sessions
│   │   ├── middleware/   # Request logging
│   │   ├── models/       # Database models
│   │   ├── routers/      # API endpoints
│   │   ├── schemas/      # Request + response shapes
│   │   ├── services/     # SOC API client, enricher, notifier
│   │   └── worker/       # Celery tasks (poll, notify, enrich)
│   ├── alembic/          # Database migrations
│   ├── tests/            # pytest suite
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── app/          # Pages + Next.js API routes
    │   ├── components/   # UI components
    │   └── lib/          # API client, hooks, schemas, utilities
    └── tests/
        ├── unit/         # Vitest unit tests
        └── e2e/          # Playwright end-to-end tests
```
