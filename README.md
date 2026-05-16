# RU Course Sniper

A production-quality web application that monitors Rutgers course availability and sends instant notifications when watched index numbers open up.

> **This tool does NOT automate enrollment.** It only detects availability and notifies you — you still need to manually enroll in WebReg.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind v4, shadcn/ui |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2 (async) |
| Worker | Celery + Redis (polling, notification dispatch) |
| Database | PostgreSQL 16 with Row-Level Security |
| Auth | JWT (httpOnly cookie BFF pattern) |

---

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (for Postgres + Redis)
- `make`

---

## First-Time Setup

```bash
git clone <repo>
cd RU-Course-Sniper

make setup
```

This creates the Python venv, installs all backend and frontend dependencies.

Then copy the example env file and fill in your secrets:

```bash
cp backend/.env.example backend/.env
# edit backend/.env — set SECRET_KEY, FERNET_KEY, DATABASE_URL, etc.
```

---

## Running Locally

### Everything at once

```bash
make dev
```

Starts Postgres + Redis in Docker (detached), then launches the backend and frontend side by side. Hit `Ctrl-C` to stop both.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/api/docs |

### Individual services

```bash
make infra          # Postgres + Redis only (Docker, detached)
make dev-backend    # uvicorn --reload on :8000
make dev-frontend   # next dev on :3000
make infra-down     # stop Postgres + Redis
```

---

## Testing

### Run all tests

```bash
make test
```

### Backend only (pytest)

```bash
make test-backend
```

The backend test suite uses a separate `course_sniper_test` database. Make sure the database is running (`make infra`) before running tests.

Individual pytest options work too:

```bash
cd backend
.venv/bin/pytest -v                        # verbose
.venv/bin/pytest tests/test_auth.py -v     # single file
.venv/bin/pytest -k "isolation" -v         # by keyword
```

### Frontend only (Vitest)

```bash
make test-frontend
```

Or with watch mode for active development:

```bash
cd frontend
npm run test:watch
```

### End-to-end tests (Playwright)

Requires the full stack running (`make dev` in another terminal):

```bash
cd frontend
npm run test:e2e
npm run test:e2e:ui   # interactive UI mode
```

---

## Linting & Type Checking

```bash
make lint           # all checks

make lint-backend   # ruff (lint + format) + mypy
make lint-frontend  # eslint + tsc --noEmit
```

---

## Database Migrations

```bash
cd backend
.venv/bin/alembic upgrade head       # apply all migrations
.venv/bin/alembic downgrade -1       # roll back one migration
.venv/bin/alembic revision --autogenerate -m "description"  # new migration
```

---

## Environment Variables

Key variables in `backend/.env`:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Async Postgres URL (`postgresql+asyncpg://...`) |
| `SYNC_DATABASE_URL` | Yes | Sync Postgres URL for Celery workers |
| `REDIS_URL` | Yes | Redis connection URL |
| `SECRET_KEY` | Yes | JWT signing key (any random 32+ char string) |
| `FERNET_KEY` | Yes | Credential encryption key — generate with: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ENVIRONMENT` | No | `development` / `staging` / `production` (default: `development`) |
| `SENTRY_DSN` | No | Sentry error tracking DSN |

---

## How It Works

1. **Polling** — A Celery Beat task polls the Rutgers SOC API every 20 seconds (configurable). One central poll serves all users — not one poll per user.

2. **Diff detection** — The worker computes newly-open indexes (closed → open transitions) against the previous poll state stored in Redis.

3. **Watchlist matching** — Newly-open indexes are matched against all active user watchlists in Postgres.

4. **Notification dispatch** — A `dispatch_notification` task is enqueued per matched user. It decrypts their stored credentials and sends via Discord webhook or Pushover. Delivery is idempotent — a Redis dedup key prevents double-sending within the same open event.

5. **Re-notification** — When an index closes, the dedup key is deleted. If the same index reopens later, the user is notified again.

6. **Enrichment** — Course details (subject, title, instructor, meeting times) are fetched from the SOC API every 10 minutes and cached in Redis. Notifications fire even if enrichment is unavailable — they'll just show the index number.

---

## Project Structure

```
RU-Course-Sniper/
├── Makefile
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI dependencies (auth, DB sessions)
│   │   ├── core/         # Config, security, logging
│   │   ├── db/           # SQLAlchemy engine + session factories
│   │   ├── middleware/   # Request logging (ASGI)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── routers/      # API route handlers
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # SOC API client, enricher, notifier
│   │   └── worker/       # Celery app + tasks (poll, notify, enrich)
│   ├── alembic/          # Database migrations
│   ├── tests/            # pytest test suite
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── app/          # Next.js App Router pages + API routes
    │   ├── components/   # UI components
    │   └── lib/          # API client, hooks, schemas, utils
    └── tests/
        ├── unit/         # Vitest unit tests
        └── e2e/          # Playwright end-to-end tests
```

---

## Notes

- Polling interval defaults to 20 seconds. Don't set it below 10 seconds — be respectful of the Rutgers SOC API.
- The tool notifies you; it does not enroll you. You must act on the notification in WebReg manually.
