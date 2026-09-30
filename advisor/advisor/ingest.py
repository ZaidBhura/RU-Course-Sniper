"""Import one term of SOC course data into the advisor catalog.

Usage:
    python -m advisor.ingest --year 2026 --term 9 --campus NB --file courses.json
    python -m advisor.ingest --year 2026 --term 9 --campus NB          # live fetch

Each import is a full snapshot of the term, applied in one transaction:
the term's existing offerings (and their sections/meetings) are replaced.
Re-running the same import is safe and yields the same result. `course`,
`core_code` and `instructor` rows are shared across terms and upserted.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from advisor.db import make_engine
from advisor.models import (
    CoreCode,
    Course,
    CourseOffering,
    Instructor,
    Meeting,
    OfferingCoreCode,
    Section,
    SectionInstructor,
    Term,
)
from advisor.soc import normalize as soc
from advisor.soc.client import fetch_courses, validate_term
from advisor.soc.normalize import ParseResult, normalize_instructor_name, parse_courses
from advisor.soc.prereqs import parse_prereqs

log = logging.getLogger(__name__)

MAX_FILE_BYTES = 200 * 1024 * 1024
CHUNK = 1000

Row = dict[str, Any]


def _chunks(rows: Sequence[Row], size: int = CHUNK) -> Iterator[Sequence[Row]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


@dataclass
class IngestSummary:
    year: int
    term: int
    campus: str
    courses: int
    sections: int
    meetings: int
    instructors: int
    skipped_records: int
    prereq_unparsed: list[str]

    def __str__(self) -> str:
        lines = [
            f"Imported {self.year}-{self.term} {self.campus}: {self.courses} courses, "
            f"{self.sections} sections, {self.meetings} meetings, "
            f"{self.instructors} instructors.",
            f"Skipped malformed records: {self.skipped_records}",
            f"Prerequisites needing manual review: {len(self.prereq_unparsed)}",
        ]
        lines += [f"  - {c}" for c in self.prereq_unparsed]
        return "\n".join(lines)


def load_file(path: Path) -> Any:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"{path} is {size} bytes; refusing files over {MAX_FILE_BYTES}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def ingest_payload(
    engine: Engine, payload: Any, year: int, term: int, campus: str
) -> IngestSummary:
    validate_term(year, term, campus)
    parsed = parse_courses(payload)
    with engine.begin() as conn:
        return _write(conn, parsed, year, term, campus)


def _write(
    conn: Connection, parsed: ParseResult, year: int, term: int, campus: str
) -> IngestSummary:
    courses = parsed.courses

    term_id = conn.execute(
        insert(Term)
        .values(year=year, term=term, campus=campus, last_ingested_at=func.now())
        .on_conflict_do_update(
            index_elements=["year", "term", "campus"], set_={"last_ingested_at": func.now()}
        )
        .returning(Term.id)
    ).scalar_one()

    # Core codes (shared lookup).
    codes = {c.code: c.description for course in courses for c in course.core_codes}
    if codes:
        code_ins = insert(CoreCode)
        conn.execute(
            code_ins.on_conflict_do_update(
                index_elements=["code"], set_={"description": code_ins.excluded.description}
            ),
            [{"code": k, "description": v} for k, v in sorted(codes.items())],
        )

    # Courses (stable identity across terms).
    course_ids: dict[tuple[str, str], int] = {}
    course_rows: list[Row] = [
        {
            "course_string": c.course_string,
            "supplement_code": c.supplement_code,
            "school_code": c.school_code,
            "subject_code": c.subject_code,
            "course_number": c.course_number,
            "title": c.title,
        }
        for c in courses
    ]
    for chunk in _chunks(course_rows):
        course_ins = insert(Course)
        course_stmt = course_ins.on_conflict_do_update(
            index_elements=["course_string", "supplement_code"],
            set_={"title": course_ins.excluded.title},
        ).returning(Course.id, Course.course_string, Course.supplement_code)
        for course_row in conn.execute(course_stmt, list(chunk)):
            course_ids[(course_row.course_string, course_row.supplement_code)] = course_row.id

    # Replace this term's snapshot. Cascades to core codes, sections, meetings.
    conn.execute(delete(CourseOffering).where(CourseOffering.term_id == term_id))

    unparsed: list[str] = []
    offering_rows: list[Row] = []
    for c in courses:
        prereq = parse_prereqs(c.prereq_raw)
        if not prereq.ok:
            unparsed.append(f"{c.course_string}: {prereq.raw[:80]}")
        offering_rows.append(
            {
                "term_id": term_id,
                "course_id": course_ids[(c.course_string, c.supplement_code)],
                "title": c.title,
                "expanded_title": c.expanded_title,
                "school_description": c.school_description,
                "subject_description": c.subject_description,
                "level": c.level,
                "credits": c.credits,
                "credits_code": c.credits_code,
                "prereq_raw": prereq.raw,
                "prereq_tree": prereq.tree,
                "prereq_parse_ok": prereq.ok,
                "prereq_parse_error": prereq.error,
                "synopsis_url": c.synopsis_url,
                "course_notes": c.course_notes,
            }
        )
    offering_ids: dict[int, int] = {}  # course_id -> offering_id
    for chunk in _chunks(offering_rows):
        offering_stmt = insert(CourseOffering).returning(
            CourseOffering.id, CourseOffering.course_id
        )
        for offering_row in conn.execute(offering_stmt, list(chunk)):
            offering_ids[offering_row.course_id] = offering_row.id

    def offering_of(c: soc.Course) -> int:
        return offering_ids[course_ids[(c.course_string, c.supplement_code)]]

    core_rows: list[Row] = [
        {"offering_id": offering_of(c), "core_code": code}
        for c in courses
        for code in sorted({cc.code for cc in c.core_codes})
    ]
    for chunk in _chunks(core_rows):
        conn.execute(insert(OfferingCoreCode), list(chunk))

    # Instructors (shared across terms).
    names: dict[str, str] = {}
    for c in courses:
        for s in c.sections:
            for name in s.instructors:
                names.setdefault(normalize_instructor_name(name), name)
    instructor_ids: dict[str, int] = {}
    inst_rows: list[Row] = [{"normalized_name": k, "soc_name": v} for k, v in sorted(names.items())]
    for chunk in _chunks(inst_rows):
        inst_ins = insert(Instructor)
        inst_stmt = inst_ins.on_conflict_do_update(
            index_elements=["normalized_name"], set_={"soc_name": inst_ins.excluded.soc_name}
        ).returning(Instructor.id, Instructor.normalized_name)
        for inst_row in conn.execute(inst_stmt, list(chunk)):
            instructor_ids[inst_row.normalized_name] = inst_row.id

    # Sections.
    section_rows: list[Row] = []
    section_lookup: dict[tuple[int, str], soc.Section] = {}
    for c in courses:
        oid = offering_of(c)
        for s in c.sections:
            section_lookup[(oid, s.index_number)] = s
            section_rows.append(
                {
                    "offering_id": oid,
                    "index_number": s.index_number,
                    "section_number": s.section_number,
                    "open_status": s.open_status,
                    "course_type": s.course_type,
                    "campus_code": s.campus_code,
                    "exam_code": s.exam_code,
                    "final_exam": s.final_exam,
                    "cross_listed": s.cross_listed,
                    "notes": s.notes,
                    "eligibility": s.eligibility,
                    "subtitle": s.subtitle,
                }
            )
    link_rows: list[Row] = []
    meeting_rows: list[Row] = []
    for chunk in _chunks(section_rows):
        section_stmt = insert(Section).returning(
            Section.id, Section.offering_id, Section.index_number
        )
        for row in conn.execute(section_stmt, list(chunk)):
            sec = section_lookup[(row.offering_id, row.index_number)]
            for iid in sorted(
                {instructor_ids[normalize_instructor_name(n)] for n in sec.instructors}
            ):
                link_rows.append({"section_id": row.id, "instructor_id": iid})
            for m in sec.meetings:
                meeting_rows.append(
                    {
                        "section_id": row.id,
                        "day": m.day,
                        "start_min": m.start_min,
                        "end_min": m.end_min,
                        "campus_name": m.campus_name,
                        "campus_abbrev": m.campus_abbrev,
                        "building": m.building,
                        "room": m.room,
                        "mode_code": m.mode_code,
                        "mode_desc": m.mode_desc,
                    }
                )
    for chunk in _chunks(link_rows):
        conn.execute(insert(SectionInstructor), list(chunk))
    for chunk in _chunks(meeting_rows):
        conn.execute(insert(Meeting), list(chunk))

    conn.execute(
        update(Term)
        .where(Term.id == term_id)
        .values(course_count=len(courses), section_count=len(section_rows))
    )
    total_instructors = conn.execute(select(func.count()).select_from(Instructor)).scalar_one()

    return IngestSummary(
        year=year,
        term=term,
        campus=campus,
        courses=len(courses),
        sections=len(section_rows),
        meetings=len(meeting_rows),
        instructors=total_instructors,
        skipped_records=parsed.skipped,
        prereq_unparsed=unparsed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import SOC course data for one term.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument(
        "--term", type=int, required=True, help="0 winter, 1 spring, 7 summer, 9 fall"
    )
    parser.add_argument("--campus", default="NB")
    parser.add_argument("--file", type=Path, help="saved courses.json; omit to fetch live")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    validate_term(args.year, args.term, args.campus)
    payload = (
        load_file(args.file) if args.file else fetch_courses(args.year, args.term, args.campus)
    )
    summary = ingest_payload(make_engine(), payload, args.year, args.term, args.campus)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
