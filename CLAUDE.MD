
CLAUDE.md — RU Course Sniper Production Build Rules
Mission
Transform this Rutgers course sniper from a single-user CLI poller into a secure, multi-tenant production platform with:

Next.js frontend
robust Python backend
strong security defaults
clean architecture
zero-trust handling of user data and secrets
high test confidence and operational observability
Never optimize for speed of coding over correctness, security, and maintainability.

Fixed Tech Stack (default unless explicitly overridden)
Frontend
Next.js (App Router) + TypeScript
Tailwind + shadcn/ui
TanStack Query for server-state
Zod for runtime validation
Playwright for E2E tests
Backend
FastAPI (Python 3.12+)
Pydantic v2 + SQLAlchemy 2.0 (async)
Alembic migrations
Background worker process for polling + fanout
Data + Infra
PostgreSQL (primary database)
Redis (queue/cache/rate-limit primitives)
Celery (or Dramatiq) workers for scheduled polling, notification dispatch, retries
Docker + Docker Compose for local/prod parity
Deploy on managed platform (Fly/Render/Railway/AWS), HTTPS-only
Observability & Security Tooling
Structured logs (JSON), request IDs, trace IDs
OpenTelemetry tracing + Prometheus metrics
Sentry for exceptions
CI security checks: Bandit, pip-audit, npm audit, Semgrep, Trivy (containers)
Current Project Context (important)
Existing Python modules (SOC client, watcher, enricher, notifier, command handler) are the business core.
When migrating:

Preserve existing polling logic semantics.
Extract reusable domain logic into backend services.
Do not break alert behavior (Discord/Pushover equivalents) during transition.
Target Production Architecture
Use a multi-service model:

web (Next.js):

Authenticated dashboard
Manage watchlists, terms/campus, notification channels
View event history and system status
api (FastAPI):

AuthN/AuthZ, tenancy boundaries
CRUD for users/watchlists/notifications
OpenAPI-first contracts
Idempotent endpoints
worker:

Poll Rutgers SOC centrally per term/campus (not per user)
Compute diff of newly open indexes
Match against user watchlists
Dispatch notifications with retries and dedupe keys
db (Postgres):

Users, watchlists, watchlist_items, availability_events, notifications, delivery_attempts, audit_logs
redis:

job queue + distributed locks + burst control
Non-Negotiable Security Rules
Always enforce:

Tenant isolation on every query and endpoint
Input validation for all external/user inputs
Output encoding and safe rendering in UI
Secrets only via environment/secret manager (never in code or logs)
Hashed/encrypted sensitive fields where applicable
Rate limits per user/IP + abuse detection
Idempotency keys for write/retry-sensitive operations
CSRF protection for cookie-auth flows
Strict CORS allowlist
Principle of least privilege for service credentials
Dependency pinning and vulnerability scanning in CI
Never claim “fully secure” or “zero vulnerabilities”; instead produce measurable controls and residual risk notes.

Reliability & Scale Requirements
Polling must be centralized and deduplicated.
External API failures must use exponential backoff + jitter.
All notification sends must be retryable and idempotent.
Exactly-once is not assumed; design for at-least-once with dedupe.
Add dead-letter queue and replay tooling.
Ensure graceful degradation when Rutgers API is degraded.
Provide migration/rollback scripts for schema changes.
UI/UX Standards
Clean, modern, minimal dashboard
Mobile responsive by default
WCAG 2.1 AA accessibility baseline
Loading/empty/error states for every async view
Clear success/failure feedback for watchlist and notification actions
Audit/event timeline for user trust
Engineering Workflow for Every Task
For each task, produce:

Brief plan
Proposed changes by layer (web/api/worker/db)
Security impact
Test plan
Rollback plan (if schema or infra touched)
Then implement in small commits with tests.

Agents vs Skills Usage Policy
Use Skills for reusable standards
Create and apply persistent skills:

backend-security-hardening
fastapi-architecture
nextjs-ui-system
multi-tenant-data-modeling
ci-cd-release-gates
observability-incident-readiness
Use Agents for bounded execution
Run specialized agents in parallel when possible:

Security agent: threat model + authz review
Backend agent: API/data model correctness
Worker agent: queue/retry/idempotency
Frontend agent: UX/accessibility/state management
QA agent: integration/load/failure testing
Use direct instructions for each task
Each prompt must include:

business goal
constraints
acceptance criteria
required artifacts (tests, docs, risk notes)
Definition of Done (must pass before merge)
Type checks, lint, unit/integration/E2E tests pass
Migration is reversible and validated
Security scans pass or have explicit approved exceptions
Observability hooks added for new critical flows
Performance impact assessed for hot paths
Documentation updated (API, env vars, runbook, architecture notes)
No merge without DoD.

Priority Migration Plan (execute in this order)
Introduce Postgres schema + tenancy model
Build FastAPI auth + watchlist APIs
Move poller to worker with Redis queue + dedupe
Add notification delivery pipeline + retries
Build Next.js dashboard (auth, watchlists, status)
Add observability + alerting + runbooks
Harden CI/CD with security/release gates
Load test and failure-injection test before production cutover
Output Format Required From Claude
For implementation requests, always return:

“Plan”
“Changes”
“Security checks”
“Tests added/updated”
“Risks & follow-ups”
Keep responses concise, concrete, and production-focused.