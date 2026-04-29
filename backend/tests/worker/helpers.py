"""Shared test helpers for worker task tests."""

import uuid
from unittest.mock import MagicMock


def make_watched_index(index_number: int = 11643, semester_code: str = "12026", is_active: bool = True):
    """Return a MagicMock resembling a WatchedIndex ORM row."""
    wi = MagicMock()
    wi.id = uuid.uuid4()
    wi.user_id = uuid.uuid4()
    wi.tenant_id = uuid.uuid4()
    wi.index_number = index_number
    wi.semester_code = semester_code
    wi.label = None
    wi.is_active = is_active
    return wi
