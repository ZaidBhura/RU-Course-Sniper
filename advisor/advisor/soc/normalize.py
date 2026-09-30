"""Turn raw SOC `courses.json` records into validated, typed records.

The SOC API is undocumented and untrusted input: every field is read
defensively, and records that fail validation are skipped and counted rather
than crashing an import.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from advisor.soc.prereqs import COURSE_RE

log = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"\d{5}")
_MILITARY_RE = re.compile(r"\d{4}")
_VALID_DAYS = {"M", "T", "W", "H", "F", "S", "U"}

MAX_TEXT = 4000  # guard against unexpectedly huge free-text fields


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _minutes(military: Any) -> int | None:
    """'1550' -> 950. Returns None for blank or malformed times."""
    raw = _text(military)
    if not _MILITARY_RE.fullmatch(raw):
        return None
    hours, minutes = int(raw[:2]), int(raw[2:])
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def normalize_instructor_name(name: str) -> str:
    """'SELIM, SAMAH' -> 'selim, samah'. Used as the dedupe key."""
    return re.sub(r"\s+", " ", name).strip().lower()


@dataclass
class Meeting:
    day: str
    start_min: int | None
    end_min: int | None
    campus_name: str
    campus_abbrev: str
    building: str
    room: str
    mode_code: str
    mode_desc: str


@dataclass
class Section:
    index_number: str
    section_number: str
    open_status: bool
    instructors: list[str]
    course_type: str
    campus_code: str
    exam_code: str
    final_exam: str
    cross_listed: str
    notes: str
    eligibility: str
    subtitle: str
    meetings: list[Meeting] = field(default_factory=list)


@dataclass
class CoreCode:
    code: str
    description: str


@dataclass
class Course:
    course_string: str
    supplement_code: str
    school_code: str
    school_description: str
    subject_code: str
    subject_description: str
    course_number: str
    title: str
    expanded_title: str
    level: str
    credits: Decimal | None
    credits_code: str
    prereq_raw: str
    synopsis_url: str
    course_notes: str
    core_codes: list[CoreCode]
    sections: list[Section]


def _parse_credits(record: dict[str, Any]) -> tuple[Decimal | None, str]:
    obj = record.get("creditsObject") or {}
    code = _text(obj.get("code") if isinstance(obj, dict) else "", 16)
    raw = record.get("credits")
    if raw is None:
        return None, code  # "BA" = by arrangement
    try:
        value = Decimal(str(raw))
    except InvalidOperation:
        return None, code
    if value < 0 or value > 30:
        return None, code
    return value, code


def _parse_meeting(raw: dict[str, Any]) -> Meeting:
    day = _text(raw.get("meetingDay"), 2)
    return Meeting(
        day=day if day in _VALID_DAYS else "",
        start_min=_minutes(raw.get("startTimeMilitary")),
        end_min=_minutes(raw.get("endTimeMilitary")),
        campus_name=_text(raw.get("campusName"), 64),
        campus_abbrev=_text(raw.get("campusAbbrev"), 16),
        building=_text(raw.get("buildingCode"), 16),
        room=_text(raw.get("roomNumber"), 16),
        mode_code=_text(raw.get("meetingModeCode"), 8),
        mode_desc=_text(raw.get("meetingModeDesc"), 64),
    )


def _parse_section(raw: dict[str, Any]) -> Section | None:
    index = _text(raw.get("index"), 8)
    if not _INDEX_RE.fullmatch(index):
        return None
    instructors = []
    for item in raw.get("instructors") or []:
        if isinstance(item, dict) and _text(item.get("name")):
            instructors.append(_text(item["name"], 128))
    meetings = [_parse_meeting(m) for m in raw.get("meetingTimes") or [] if isinstance(m, dict)]
    return Section(
        index_number=index,
        section_number=_text(raw.get("number"), 8),
        open_status=bool(raw.get("openStatus")),
        instructors=instructors,
        course_type=_text(raw.get("sectionCourseType"), 4),
        campus_code=_text(raw.get("campusCode"), 8),
        exam_code=_text(raw.get("examCode"), 4),
        final_exam=_text(raw.get("finalExam"), 128),
        cross_listed=_text(raw.get("crossListedSectionsText"), 512),
        notes=_text(raw.get("sectionNotes")),
        eligibility=_text(raw.get("sectionEligibility")),
        subtitle=_text(raw.get("subtitle"), 256),
        meetings=meetings,
    )


def parse_course(record: Any) -> Course | None:
    if not isinstance(record, dict):
        return None
    course_string = _text(record.get("courseString"), 16)
    if not COURSE_RE.fullmatch(course_string):
        return None
    school_code, subject_code, course_number = course_string.split(":")
    school = record.get("school") or {}

    core_codes: list[CoreCode] = []
    for item in record.get("coreCodes") or []:
        if not isinstance(item, dict):
            continue
        code = _text(item.get("coreCode") or item.get("code"), 16)
        if code:
            desc = _text(item.get("coreCodeDescription") or item.get("description"), 256)
            core_codes.append(CoreCode(code=code, description=desc))

    sections = []
    for raw_section in record.get("sections") or []:
        if isinstance(raw_section, dict):
            parsed = _parse_section(raw_section)
            if parsed is not None:
                sections.append(parsed)

    credits, credits_code = _parse_credits(record)
    return Course(
        course_string=course_string,
        supplement_code=_text(record.get("supplementCode"), 4),
        school_code=school_code,
        school_description=_text(
            school.get("description") if isinstance(school, dict) else "", 256
        ),
        subject_code=subject_code,
        subject_description=_text(record.get("subjectDescription"), 256),
        course_number=course_number,
        title=_text(record.get("title"), 256),
        expanded_title=_text(record.get("expandedTitle"), 512),
        level=_text(record.get("level"), 2),
        credits=credits,
        credits_code=credits_code,
        prereq_raw=_text(record.get("preReqNotes")),
        synopsis_url=_text(record.get("synopsisUrl"), 512),
        course_notes=_text(record.get("courseNotes")),
        core_codes=core_codes,
        sections=sections,
    )


@dataclass
class ParseResult:
    courses: list[Course]
    skipped: int


def parse_courses(payload: Any) -> ParseResult:
    """Parse a full courses.json payload, merging duplicate course records.

    SOC sometimes lists the same course + supplement twice (seen in graduate
    schools); their sections are merged under one course.
    """
    if isinstance(payload, dict) and "courses" in payload:
        payload = payload["courses"]
    if not isinstance(payload, list):
        raise ValueError("courses.json payload must be a list of courses")

    merged: dict[tuple[str, str], Course] = {}
    skipped = 0
    for record in payload:
        course = parse_course(record)
        if course is None:
            skipped += 1
            continue
        key = (course.course_string, course.supplement_code)
        if key in merged:
            existing = merged[key]
            known = {s.index_number for s in existing.sections}
            existing.sections.extend(s for s in course.sections if s.index_number not in known)
            codes = {c.code for c in existing.core_codes}
            existing.core_codes.extend(c for c in course.core_codes if c.code not in codes)
        else:
            merged[key] = course
    if skipped:
        log.warning("soc.parse.skipped_records count=%d", skipped)
    return ParseResult(courses=list(merged.values()), skipped=skipped)
