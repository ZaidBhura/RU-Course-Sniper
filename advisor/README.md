# Advisor (side project on the `advisor-agent` branch)

An academic advisor agent for RU Course Sniper. Given a student's transcript,
major and interests, it audits degree progress and proposes a semester plan
with sections and professors. It lives in its own folder, database schema and
CI workflow so it can be merged into the main app later without touching the
sniper backend.

MVP scope: New Brunswick, SAS Core, Computer Science major.

## Status

| Milestone | What | State |
|---|---|---|
| 1 | Course catalog: SOC import, prerequisite parser | Done |
| 2 | Transcript parser (PDF to confirmed course list) | Needs sample transcripts |
| 3 | Requirement rules (SAS Core + CS) and audit engine | Needs catalog year + Degree Navigator audit |
| 4 | Planner (eligible, useful, balanced, sections) | |
| 5 | Rate My Professors + Reddit summaries (pgvector) | |
| 6 | Agent layer + API endpoints, then merge into main app | |

## Setup

```bash
cd advisor
docker compose up -d                                   # Postgres 16 + pgvector on :5433
docker compose exec advisor-db createdb -U advisor advisor_test
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env && set -a && . ./.env && set +a
alembic upgrade head
```

## Importing course data

```bash
# From a saved file
python -m advisor.ingest --year 2026 --term 9 --campus NB --file courses.json
# Live from the SOC API
python -m advisor.ingest --year 2026 --term 9 --campus NB
```

Terms: 0 winter, 1 spring, 7 summer, 9 fall. Each import replaces that term's
snapshot in one transaction, so re-running is safe. Import past terms too: a
degree audit needs the core codes a course carried in the term the student took
it, and those change over time.

Fall 2026 NB (full file, all schools): 4,385 courses, 12,011 sections,
17,474 meetings, 4,023 instructors, in about 4 seconds.

## Data model

All tables live in the `advisor` Postgres schema. Catalog data is public, so it
is not tenant-scoped. Student data (transcripts, plans) will get separate,
tenant-scoped tables following the main app's RLS approach.

- `course`: stable identity across terms (`01:198:344` + supplement code)
- `course_offering`: a course in one term, with credits, parsed prerequisites
  and core codes (`offering_core_code`)
- `section`, `meeting`, `instructor`, `section_instructor`
- `term`, `core_code`

## Prerequisites

SOC `preReqNotes` is free text. `advisor/soc/prereqs.py` parses it into a JSON
tree stored in `course_offering.prereq_tree`, and `is_satisfied(tree, completed)`
checks it. On the Fall 2026 file, 1,232 of 1,234 notes parse. The 2 that don't
("TWO Course Within the Subject Area:") list no courses, so they are stored with
`prereq_parse_ok = false` for manual review rather than guessed.

The parser only checks course completion. It does not model minimum grades,
placement tests, or instructor permission, since SOC notes don't include them.

## Tests

```bash
pytest                      # DB tests skip unless ADVISOR_TEST_DATABASE_URL is set
ruff check advisor tests alembic/env.py && mypy advisor && bandit -r advisor -ll
```

The test fixture `tests/fixtures/soc_sample.json` is a slice of the real
Fall 2026 file (CS, math, and the unusual prerequisite formats).
