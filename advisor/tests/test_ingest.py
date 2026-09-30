import json
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import func, select, text

from advisor.ingest import ingest_payload
from advisor.models import (
    Course,
    CourseOffering,
    Instructor,
    Meeting,
    OfferingCoreCode,
    Section,
    Term,
)
from advisor.soc.prereqs import is_satisfied

FIXTURE = Path(__file__).parent / "fixtures" / "soc_sample.json"


def _count(conn, model):
    return conn.execute(select(func.count()).select_from(model)).scalar_one()


@pytest.fixture
def engine(migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE advisor.term, advisor.course, advisor.core_code, "
                "advisor.instructor RESTART IDENTITY CASCADE"
            )
        )
    return migrated_engine


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


def test_ingest_writes_catalog(engine, payload):
    summary = ingest_payload(engine, payload, 2026, 9, "NB")
    assert summary.courses == 16
    assert summary.prereq_unparsed and summary.prereq_unparsed[0].startswith("01:730:295")

    with engine.connect() as conn:
        assert _count(conn, Course) == 16
        assert _count(conn, CourseOffering) == 16
        assert _count(conn, Section) == summary.sections
        assert _count(conn, Meeting) == summary.meetings
        term = conn.execute(select(Term)).one()
        assert (term.year, term.term, term.campus) == (2026, 9, "NB")
        assert term.section_count == summary.sections

        tree = conn.execute(
            select(CourseOffering.prereq_tree)
            .join(Course, Course.id == CourseOffering.course_id)
            .where(Course.course_string == "01:198:206")
        ).scalar_one()
        assert is_satisfied(tree, {"01:198:205", "01:640:152"})

        qr = (
            conn.execute(
                select(Course.course_string)
                .join(CourseOffering, CourseOffering.course_id == Course.id)
                .join(OfferingCoreCode, OfferingCoreCode.offering_id == CourseOffering.id)
                .where(OfferingCoreCode.core_code == "QR")
            )
            .scalars()
            .all()
        )
        assert "01:640:151" in qr


def test_reingest_is_idempotent(engine, payload):
    first = ingest_payload(engine, payload, 2026, 9, "NB")
    with engine.connect() as conn:
        before = [_count(conn, m) for m in (Course, CourseOffering, Section, Meeting, Instructor)]
    second = ingest_payload(engine, payload, 2026, 9, "NB")
    with engine.connect() as conn:
        after = [_count(conn, m) for m in (Course, CourseOffering, Section, Meeting, Instructor)]
    assert before == after
    assert first.sections == second.sections


def test_second_term_shares_courses_and_instructors(engine, payload):
    ingest_payload(engine, payload, 2026, 9, "NB")
    ingest_payload(engine, payload, 2027, 1, "NB")
    with engine.connect() as conn:
        assert _count(conn, Term) == 2
        assert _count(conn, Course) == 16
        assert _count(conn, CourseOffering) == 32


def test_snapshot_replaces_removed_sections(engine, payload):
    ingest_payload(engine, payload, 2026, 9, "NB")
    trimmed = [dict(c, sections=[]) for c in payload]
    ingest_payload(engine, trimmed, 2026, 9, "NB")
    with engine.connect() as conn:
        assert _count(conn, Section) == 0
        assert _count(conn, Meeting) == 0


def test_invalid_term_rejected(engine, payload):
    with pytest.raises(ValueError):
        ingest_payload(engine, payload, 2026, 5, "NB")
    with pytest.raises(ValueError):
        ingest_payload(engine, payload, 2026, 9, "XX")


def test_failed_import_rolls_back(engine, payload, monkeypatch):
    ingest_payload(engine, payload, 2026, 9, "NB")
    with engine.connect() as conn:
        sections_before = _count(conn, Section)

    import advisor.ingest as ingest_mod

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure mid-import")

    monkeypatch.setattr(ingest_mod, "normalize_instructor_name", boom)
    with pytest.raises(RuntimeError):
        ingest_payload(engine, payload, 2026, 9, "NB")
    with engine.connect() as conn:
        assert _count(conn, Section) == sections_before


def test_migration_downgrade_and_upgrade(migrated_engine, alembic_cfg):
    command.downgrade(alembic_cfg, "base")
    with migrated_engine.connect() as conn:
        left = conn.execute(
            text(
                "select count(*) from information_schema.tables "
                "where table_schema = 'advisor' and table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert left == 0
    command.upgrade(alembic_cfg, "head")
