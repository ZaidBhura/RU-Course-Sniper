"""Synchronous HTTP client for the Rutgers SOC (Schedule of Classes) API.

semester_code format: {term}{year}  e.g. "12026" = term 1 (Spring), year 2026
term digit: 0=Winter, 1=Spring, 7=Summer, 9=Fall
campus defaults to "NB" (New Brunswick).
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "RUCourseSniper/2.0"})


@dataclass
class OpenSection:
    index_number: int


@dataclass
class CourseDetail:
    subject: str
    course_number: str
    section: str
    title: str
    instructors: list[str]
    meeting_times: list[str]
    index_number: int


def _parse_semester_code(semester_code: str) -> tuple[int, int, str]:
    """Return (year, term, campus) from a Rutgers semester_code string.

    Rutgers semester_code is a 5-char string: first digit = term, last 4 = year.
    e.g. "12026" → term=1 (Spring), year=2026, campus="NB"
    """
    term = int(semester_code[0])
    year = int(semester_code[1:])
    return year, term, "NB"


def _request_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: int = 10,
) -> Optional[object]:
    """GET url with exponential backoff + jitter. Returns parsed JSON or None."""
    for attempt in range(max_retries):
        try:
            response = _SESSION.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries - 1:
                logger.error("SOC API request failed after %d attempts: %s", max_retries, exc)
                return None
            wait = backoff_factor * (2**attempt) + random.uniform(0, 0.5)
            logger.warning("SOC API attempt %d failed (%s), retrying in %.1fs", attempt + 1, exc, wait)
            time.sleep(wait)
    return None


def fetch_open_sections(semester_code: str) -> list[OpenSection]:
    """Fetch currently-open section index numbers for the given semester.

    Returns an empty list on any API failure — caller must handle gracefully.
    """
    year, term, campus = _parse_semester_code(semester_code)
    url = f"https://sis.rutgers.edu/soc/api/openSections.json?year={year}&term={term}&campus={campus}"
    data = _request_with_retry(url)
    if data is None:
        return []

    if isinstance(data, list):
        sections = data
    elif isinstance(data, dict) and "openSections" in data:
        sections = data["openSections"]
    else:
        logger.warning("Unexpected openSections response type: %s", type(data))
        return []

    result: list[OpenSection] = []
    for item in sections:
        try:
            if isinstance(item, str):
                result.append(OpenSection(index_number=int(item)))
            elif isinstance(item, dict):
                result.append(OpenSection(index_number=int(item["indexNumber"])))
        except (ValueError, KeyError, TypeError) as exc:
            logger.debug("Skipping malformed open section entry: %s (%s)", item, exc)
    return result


def fetch_courses(semester_code: str) -> dict[int, CourseDetail]:
    """Fetch all course details and return an index_number → CourseDetail mapping.

    Returns an empty dict on any API failure — enrichment is always optional.
    """
    year, term, campus = _parse_semester_code(semester_code)
    url = f"https://sis.rutgers.edu/soc/api/courses.json?year={year}&term={term}&campus={campus}"
    data = _request_with_retry(url)
    if data is None:
        return {}

    if isinstance(data, list):
        courses = data
    elif isinstance(data, dict) and "courses" in data:
        courses = data["courses"]
    else:
        logger.warning("Unexpected courses response type: %s", type(data))
        return {}

    index_map: dict[int, CourseDetail] = {}
    for course in courses:
        if not isinstance(course, dict):
            continue
        for section in course.get("sections", []):
            if not isinstance(section, dict):
                continue
            try:
                index_number = int(section["index"])
            except (KeyError, ValueError, TypeError):
                continue

            instructors = [
                i["name"] for i in section.get("instructors", []) if isinstance(i, dict) and "name" in i
            ]
            meeting_times: list[str] = []
            for mt in section.get("meetingTimes", []):
                if not isinstance(mt, dict):
                    continue
                parts = []
                if mt.get("meetingDay"):
                    parts.append(mt["meetingDay"])
                if mt.get("startTime") and mt.get("endTime"):
                    parts.append(f"{mt['startTime']}-{mt['endTime']}")
                if mt.get("campusName"):
                    parts.append(mt["campusName"])
                if parts:
                    meeting_times.append(" ".join(parts))

            index_map[index_number] = CourseDetail(
                subject=course.get("subject", ""),
                course_number=course.get("courseNumber", ""),
                section=section.get("number", ""),
                title=course.get("title", ""),
                instructors=instructors,
                meeting_times=meeting_times,
                index_number=index_number,
            )
    return index_map
