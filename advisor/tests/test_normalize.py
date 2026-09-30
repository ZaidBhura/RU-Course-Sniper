import json
from decimal import Decimal
from pathlib import Path

import pytest

from advisor.soc.normalize import normalize_instructor_name, parse_course, parse_courses

FIXTURE = Path(__file__).parent / "fixtures" / "soc_sample.json"


@pytest.fixture(scope="module")
def payload():
    return json.loads(FIXTURE.read_text())


def test_parses_all_fixture_records_and_merges_duplicates(payload):
    result = parse_courses(payload)
    assert result.skipped == 0
    keys = [(c.course_string, c.supplement_code) for c in result.courses]
    assert len(keys) == len(set(keys))
    # 16:400:513 is listed twice with the same supplement: merged to one course.
    assert sum(1 for k in keys if k[0] == "16:400:513") == 1
    # 01:750:193 lecture and LB lab are different supplements: kept apart.
    assert {k for k in keys if k[0] == "01:750:193"} == {("01:750:193", ""), ("01:750:193", "LB")}


def test_course_fields(payload):
    courses = {c.course_string: c for c in parse_courses(payload).courses}
    algo = courses["01:198:344"]
    assert algo.credits == Decimal("4")
    assert algo.school_code == "01" and algo.subject_code == "198"
    assert algo.sections and all(len(s.index_number) == 5 for s in algo.sections)
    meeting = algo.sections[0].meetings[0]
    assert meeting.day in {"M", "T", "W", "H", "F", "S", "U"}
    assert meeting.start_min is not None and 0 <= meeting.start_min < 24 * 60


def test_by_arrangement_credits_are_null(payload):
    courses = {c.course_string: c for c in parse_courses(payload).courses}
    indep = courses["01:198:493"]
    assert indep.credits is None
    assert indep.credits_code == "BA"


def test_core_codes(payload):
    courses = {c.course_string: c for c in parse_courses(payload).courses}
    codes = {c.code for c in courses["01:640:151"].core_codes}
    assert "QR" in codes


@pytest.mark.parametrize(
    "record",
    [
        None,
        "not a dict",
        {"courseString": "DROP TABLE"},
        {"courseString": "01:198:11"},
        {},
    ],
)
def test_malformed_records_are_skipped(record):
    assert parse_course(record) is None


def test_malformed_sections_and_times_are_dropped():
    course = parse_course(
        {
            "courseString": "01:198:999",
            "credits": 99,
            "sections": [
                {"index": "12;--", "meetingTimes": []},
                {
                    "index": "12345",
                    "instructors": [{"name": "  DOE,   JANE "}, {"bad": 1}, "x"],
                    "meetingTimes": [
                        {"meetingDay": "Z", "startTimeMilitary": "2599", "endTimeMilitary": "x"}
                    ],
                },
            ],
        }
    )
    assert course is not None
    assert course.credits is None  # out of range
    assert [s.index_number for s in course.sections] == ["12345"]
    section = course.sections[0]
    assert section.instructors == ["DOE,   JANE"]
    assert normalize_instructor_name(section.instructors[0]) == "doe, jane"
    assert section.meetings[0].day == ""
    assert section.meetings[0].start_min is None


def test_payload_must_be_a_list():
    with pytest.raises(ValueError):
        parse_courses({"unexpected": True})
