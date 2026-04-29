"""Unit tests for app/services/soc_client.py."""

import pytest
from unittest.mock import MagicMock, patch, call

from app.services.soc_client import (
    fetch_open_sections,
    fetch_courses,
    _parse_semester_code,
    _request_with_retry,
)


class TestParseSemesterCode:
    def test_spring_2026(self):
        year, term, campus = _parse_semester_code("12026")
        assert year == 2026
        assert term == 1
        assert campus == "NB"

    def test_fall_2026(self):
        year, term, campus = _parse_semester_code("92026")
        assert year == 2026
        assert term == 9
        assert campus == "NB"


class TestRequestWithRetry:
    def test_returns_json_on_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [1, 2, 3]
        mock_resp.raise_for_status.return_value = None

        with patch("app.services.soc_client._SESSION") as mock_session:
            mock_session.get.return_value = mock_resp
            result = _request_with_retry("http://example.com")

        assert result == [1, 2, 3]

    def test_retries_on_failure_then_succeeds(self):
        import requests as req_lib

        good_resp = MagicMock()
        good_resp.json.return_value = {"ok": True}
        good_resp.raise_for_status.return_value = None

        with patch("app.services.soc_client._SESSION") as mock_session, \
             patch("app.services.soc_client.time.sleep"):
            mock_session.get.side_effect = [
                req_lib.exceptions.ConnectionError("down"),
                good_resp,
            ]
            result = _request_with_retry("http://example.com", max_retries=3)

        assert result == {"ok": True}
        assert mock_session.get.call_count == 2

    def test_returns_none_after_all_retries_fail(self):
        import requests as req_lib

        with patch("app.services.soc_client._SESSION") as mock_session, \
             patch("app.services.soc_client.time.sleep"):
            mock_session.get.side_effect = req_lib.exceptions.ConnectionError("down")
            result = _request_with_retry("http://example.com", max_retries=3)

        assert result is None
        assert mock_session.get.call_count == 3


class TestFetchOpenSections:
    def test_parses_string_list_response(self):
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = ["11643", "99999", "00053"]
            sections = fetch_open_sections("12026")

        assert len(sections) == 3
        index_numbers = {s.index_number for s in sections}
        assert index_numbers == {11643, 99999, 53}

    def test_parses_dict_list_response(self):
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = [{"indexNumber": "11643"}, {"indexNumber": "99999"}]
            sections = fetch_open_sections("12026")

        assert {s.index_number for s in sections} == {11643, 99999}

    def test_returns_empty_on_api_failure(self):
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = None
            sections = fetch_open_sections("12026")

        assert sections == []

    def test_skips_malformed_entries(self):
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = ["11643", "not-a-number", None, "55555"]
            sections = fetch_open_sections("12026")

        assert {s.index_number for s in sections} == {11643, 55555}


class TestFetchCourses:
    def test_builds_index_map(self):
        api_response = [
            {
                "subject": "CS",
                "courseNumber": "112",
                "title": "Data Structures",
                "sections": [
                    {
                        "index": "11643",
                        "number": "01",
                        "instructors": [{"name": "Jane Doe"}],
                        "meetingTimes": [
                            {"meetingDay": "M", "startTime": "10:20", "endTime": "11:40", "campusName": "Busch"}
                        ],
                    }
                ],
            }
        ]
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = api_response
            course_map = fetch_courses("12026")

        assert 11643 in course_map
        detail = course_map[11643]
        assert detail.subject == "CS"
        assert detail.course_number == "112"
        assert detail.title == "Data Structures"
        assert detail.instructors == ["Jane Doe"]
        assert "M 10:20-11:40 Busch" in detail.meeting_times

    def test_returns_empty_on_api_failure(self):
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = None
            assert fetch_courses("12026") == {}

    def test_skips_sections_without_index(self):
        api_response = [
            {
                "subject": "CS",
                "courseNumber": "112",
                "title": "Data Structures",
                "sections": [{"number": "01"}],  # no index field
            }
        ]
        with patch("app.services.soc_client._request_with_retry") as mock_req:
            mock_req.return_value = api_response
            assert fetch_courses("12026") == {}
