"""Unit tests for app/services/enricher.py using fakeredis."""

import pytest
import fakeredis

from app.services.enricher import get_course_detail, store_course_details
from app.services.soc_client import CourseDetail


def _make_detail(index_number: int) -> CourseDetail:
    return CourseDetail(
        subject="CS",
        course_number="112",
        section="01",
        title="Data Structures",
        instructors=["Jane Doe"],
        meeting_times=["M 10:20-11:40 Busch"],
        index_number=index_number,
    )


@pytest.fixture
def r():
    return fakeredis.FakeRedis(decode_responses=True)


class TestStoreAndGetCourseDetail:
    def test_round_trip(self, r):
        detail = _make_detail(11643)
        store_course_details(r, "12026", {11643: detail})

        result = get_course_detail(r, "12026", 11643)
        assert result is not None
        assert result.subject == "CS"
        assert result.course_number == "112"
        assert result.title == "Data Structures"
        assert result.instructors == ["Jane Doe"]
        assert result.index_number == 11643

    def test_returns_none_for_missing_index(self, r):
        store_course_details(r, "12026", {11643: _make_detail(11643)})
        assert get_course_detail(r, "12026", 99999) is None

    def test_returns_none_when_cache_cold(self, r):
        assert get_course_detail(r, "12026", 11643) is None

    def test_sets_ttl(self, r):
        store_course_details(r, "12026", {11643: _make_detail(11643)}, ttl_seconds=700)
        ttl = r.ttl("sniper:course:cache:12026")
        assert 0 < ttl <= 700

    def test_overwrites_stale_cache(self, r):
        old = _make_detail(11643)
        store_course_details(r, "12026", {11643: old})

        updated = CourseDetail(
            subject="CS", course_number="112", section="02",
            title="Data Structures", instructors=["Bob Smith"],
            meeting_times=["T 1:40-3:00 Hill"], index_number=11643,
        )
        store_course_details(r, "12026", {11643: updated})

        result = get_course_detail(r, "12026", 11643)
        assert result.instructors == ["Bob Smith"]
        assert result.section == "02"

    def test_skips_store_on_empty_map(self, r):
        store_course_details(r, "12026", {})
        assert get_course_detail(r, "12026", 11643) is None

    def test_multiple_indexes(self, r):
        course_map = {i: _make_detail(i) for i in [11643, 22222, 33333]}
        store_course_details(r, "12026", course_map)

        for idx in [11643, 22222, 33333]:
            result = get_course_detail(r, "12026", idx)
            assert result is not None
            assert result.index_number == idx
