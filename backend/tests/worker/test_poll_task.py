"""Unit tests for the poll_soc Celery task.

Uses fakeredis for Redis and mocks the DB session so no live services are needed.
Verifies all state-machine behaviors ported from legacy/watcher.py.
"""

import uuid
import pytest
import fakeredis
from unittest.mock import MagicMock, patch

from app.services.soc_client import OpenSection
from tests.worker.helpers import make_watched_index


@pytest.fixture
def fake_r():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def patch_redis(fake_r):
    with patch("app.worker.tasks.poll.get_worker_redis", return_value=fake_r):
        yield fake_r


@pytest.fixture(autouse=True)
def patch_celery_task():
    """Prevent Celery from trying to connect to a broker during tests."""
    with patch("app.worker.tasks.poll.dispatch_notification") as mock_task:
        mock_task.apply_async = MagicMock()
        yield mock_task


class TestPollSocLock:
    def test_skips_when_lock_held(self, fake_r):
        fake_r.set("sniper:poll:lock:12026", "1")

        from app.worker.tasks.poll import poll_soc
        result = poll_soc.run("12026")

        assert result == {"skipped": True, "reason": "lock_held"}

    def test_releases_lock_after_run(self, fake_r):
        with patch("app.worker.tasks.poll.soc_client.fetch_open_sections", return_value=[]), \
             patch("app.worker.tasks.poll.get_worker_session") as mock_session_ctx:
            mock_session_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock(
                execute=MagicMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))),
                add=MagicMock(),
            ))
            mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.poll import poll_soc
            poll_soc.run("12026")

        assert fake_r.get("sniper:poll:lock:12026") is None

    def test_releases_lock_on_exception(self, fake_r):
        with patch("app.worker.tasks.poll.soc_client.fetch_open_sections", side_effect=RuntimeError("boom")), \
             patch("app.worker.tasks.poll.poll_soc.retry", side_effect=RuntimeError("boom")):
            from app.worker.tasks.poll import poll_soc
            with pytest.raises(RuntimeError):
                poll_soc.run("12026")

        assert fake_r.get("sniper:poll:lock:12026") is None


class TestPollSocStateTransitions:
    def _run_poll(self, fake_r, open_section_numbers, watchers=None):
        open_sections = [OpenSection(index_number=n) for n in open_section_numbers]

        with patch("app.worker.tasks.poll.soc_client.fetch_open_sections", return_value=open_sections), \
             patch("app.worker.tasks.poll._persist_state_changes", return_value=[]) as mock_persist, \
             patch("app.worker.tasks.poll.dispatch_notification") as mock_dispatch:
            mock_dispatch.apply_async = MagicMock()

            from app.worker.tasks.poll import poll_soc
            result = poll_soc.run("12026")

        return result, mock_dispatch, mock_persist

    def test_detects_newly_open(self, fake_r):
        result, mock_dispatch, mock_persist = self._run_poll(fake_r, [11643, 22222])

        assert result["newly_open"] == 2
        assert result["newly_closed"] == 0
        mock_persist.assert_called_once()
        args = mock_persist.call_args[0]
        assert args[0] == "12026"
        assert args[1] == {11643, 22222}
        assert args[2] == set()

    def test_detects_newly_closed(self, fake_r):
        # Seed previous open set
        fake_r.sadd("sniper:poll:open:12026", "11643", "22222")

        result, mock_dispatch, mock_persist = self._run_poll(fake_r, [])

        assert result["newly_closed"] == 2
        assert result["newly_open"] == 0
        mock_dispatch.apply_async.assert_not_called()
        mock_persist.assert_called_once()

    def test_no_transitions_when_state_unchanged(self, fake_r):
        fake_r.sadd("sniper:poll:open:12026", "11643")

        result, mock_dispatch, mock_persist = self._run_poll(fake_r, [11643])

        assert result["newly_open"] == 0
        assert result["newly_closed"] == 0
        mock_dispatch.apply_async.assert_not_called()
        mock_persist.assert_not_called()

    def test_updates_redis_open_set(self, fake_r):
        fake_r.sadd("sniper:poll:open:12026", "99999")  # previously open

        with patch("app.worker.tasks.poll.soc_client.fetch_open_sections",
                   return_value=[OpenSection(index_number=11643)]), \
             patch("app.worker.tasks.poll._persist_state_changes", return_value=[]), \
             patch("app.worker.tasks.poll.get_worker_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.poll import poll_soc
            poll_soc.run("12026")

        open_set = fake_r.smembers("sniper:poll:open:12026")
        assert open_set == {"11643"}
        assert "99999" not in open_set

    def test_open_set_has_ttl(self, fake_r):
        with patch("app.worker.tasks.poll.soc_client.fetch_open_sections",
                   return_value=[OpenSection(index_number=11643)]), \
             patch("app.worker.tasks.poll._persist_state_changes", return_value=[]), \
             patch("app.worker.tasks.poll.get_worker_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.poll import poll_soc
            poll_soc.run("12026")

        ttl = fake_r.ttl("sniper:poll:open:12026")
        assert 0 < ttl <= 120


class TestCloseResetDeletesDedupeKey:
    def test_dedup_key_deleted_on_close(self, fake_r):
        wi = make_watched_index(11643)

        dedup_key = f"sniper:notified:{wi.user_id}:11643:12026"
        fake_r.set(dedup_key, "1")

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [wi]

        from app.worker.tasks.poll import _write_close_reset_logs
        _write_close_reset_logs(mock_session, "12026", 11643, MagicMock(), fake_r)

        assert fake_r.get(dedup_key) is None
