"""Fetch the full course list for a term from the Rutgers SOC API.

Same endpoint and retry behavior as backend/app/services/soc_client.py, but
returns the raw payload so the importer can keep every field it needs.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

SOC_COURSES_URL = "https://sis.rutgers.edu/soc/api/courses.json"
VALID_TERMS = {0, 1, 7, 9}  # Winter, Spring, Summer, Fall
VALID_CAMPUSES = {"NB", "NK", "CM"}


class SocUnavailableError(RuntimeError):
    pass


def validate_term(year: int, term: int, campus: str) -> None:
    if not 2000 <= year <= 2100:
        raise ValueError(f"year out of range: {year}")
    if term not in VALID_TERMS:
        raise ValueError(f"term must be one of {sorted(VALID_TERMS)}, got {term}")
    if campus not in VALID_CAMPUSES:
        raise ValueError(f"campus must be one of {sorted(VALID_CAMPUSES)}, got {campus!r}")


def fetch_courses(
    year: int,
    term: int,
    campus: str = "NB",
    *,
    max_retries: int = 4,
    timeout: int = 60,
) -> Any:
    validate_term(year, term, campus)
    params: dict[str, str | int] = {"year": year, "term": term, "campus": campus}
    headers = {"User-Agent": "RUCourseSniper-Advisor/0.1"}
    for attempt in range(max_retries):
        try:
            response = requests.get(
                SOC_COURSES_URL, params=params, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == max_retries - 1:
                raise SocUnavailableError(f"SOC fetch failed after {max_retries} tries") from exc
            wait = 0.5 * (2**attempt) + random.uniform(0, 0.5)  # nosec B311
            log.warning("soc.fetch.retry attempt=%d wait=%.1fs error=%s", attempt + 1, wait, exc)
            time.sleep(wait)
    raise SocUnavailableError("unreachable")
