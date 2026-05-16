# RU Course Sniper — developer convenience targets
#
# First-time setup:
#   make setup
#
# Day-to-day:
#   make dev           — start everything (infra + backend + frontend)
#   make dev-backend   — backend only (assumes Postgres + Redis already running)
#   make dev-frontend  — frontend only

.PHONY: help setup setup-backend setup-frontend \
        infra infra-down \
        dev dev-backend dev-frontend dev-worker \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        clean

PYTHON  := backend/.venv/bin/python
UVICORN := backend/.venv/bin/uvicorn
PIP     := backend/.venv/bin/pip

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make setup          First-time: create venv + install all deps"
	@echo "  make dev            Start infra + backend + frontend"
	@echo "  make dev-backend    Backend only (Postgres + Redis must be running)"
	@echo "  make dev-frontend   Frontend only"
	@echo "  make infra          Start Postgres + Redis in Docker (detached)"
	@echo "  make infra-down     Stop Postgres + Redis containers"
	@echo "  make test           Run all tests"
	@echo "  make test-backend   Run pytest"
	@echo "  make test-frontend  Run vitest"
	@echo "  make lint           Run ruff + eslint"
	@echo "  make clean          Remove build artefacts"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: setup-backend setup-frontend
	@echo ""
	@echo "  Setup complete. Copy backend/.env.example to backend/.env and fill in secrets."
	@echo "  Then: make dev"
	@echo ""

setup-backend:
	@echo "→ Creating Python venv..."
	python3 -m venv backend/.venv
	@echo "→ Installing backend dependencies..."
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e "backend/.[dev]"

setup-frontend:
	@echo "→ Installing frontend dependencies..."
	cd frontend && npm ci

# ── Infrastructure ────────────────────────────────────────────────────────────

infra:
	@echo "→ Starting Postgres + Redis..."
	docker compose up -d postgres redis
	@echo "→ Waiting for Postgres to be ready..."
	@until docker compose exec -T postgres pg_isready -U sniper -d course_sniper > /dev/null 2>&1; do \
		printf "."; sleep 1; \
	done
	@echo " ready."

infra-down:
	docker compose stop postgres redis

# ── Dev servers ───────────────────────────────────────────────────────────────

dev: infra
	@echo "→ Starting backend + frontend + worker (Ctrl-C stops all)..."
	$(MAKE) -j3 _backend _frontend _worker

# Run backend + frontend + worker in parallel (called by dev target)
_backend: dev-backend
_frontend: dev-frontend
_worker: dev-worker

dev-backend:
	@echo "→ Backend: http://localhost:8000  (docs: http://localhost:8000/api/docs)"
	cd backend && ../${UVICORN} app.main:app --reload --port 8000

dev-frontend:
	@echo "→ Frontend: http://localhost:3000"
	cd frontend && npm run dev

dev-worker:
	@echo "→ Worker: Celery + Beat (polling + notifications)"
	cd backend && ../${PYTHON} -m celery -A app.worker.celery_app worker --beat --loglevel=info

# ── Tests ─────────────────────────────────────────────────────────────────────

test: test-backend test-frontend

test-backend:
	cd backend && ../${PYTHON} -m pytest -v

test-frontend:
	cd frontend && npm run test

# ── Lint ──────────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend

lint-backend:
	backend/.venv/bin/ruff check backend/app
	backend/.venv/bin/ruff format --check backend/app
	backend/.venv/bin/mypy backend/app

lint-frontend:
	cd frontend && npm run lint && npm run type-check

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next
