"""Unit tests for the dispatch_notification Celery task.

Verifies deduplication, credential decryption flow, NotificationLog writes,
and correct handling of missing/inactive watched indexes.
"""

import json
import uuid
import pytest
import fakeredis
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet

from app.services.notifier import SendResult
from tests.worker.helpers import make_watched_index


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fernet_key() -> str:
    return Fernet.generate_key().decode()


def _encrypt(key: str, plaintext: str) -> bytes:
    return Fernet(key.encode()).encrypt(plaintext.encode())


def _make_channel(channel_type: str, credential_blob: bytes):
    ch = MagicMock()
    ch.channel_type = channel_type
    ch.is_active = True
    ch.credential_blob = credential_blob
    return ch


@pytest.fixture
def fake_r():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def fernet_key():
    return _fernet_key()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDispatchNotificationDedup:
    def test_skips_when_already_notified(self, fake_r, fernet_key):
        wi = make_watched_index()
        dedup_key = f"sniper:notified:{wi.user_id}:11643:12026"
        fake_r.set(dedup_key, "1")

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx, \
             patch("app.core.config.settings.FERNET_KEY", fernet_key):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(wi.id), 11643, "12026")

        assert result["status"] == "skipped"
        assert result["reason"] == "already_notified"

    def test_sets_dedup_key_after_success(self, fake_r, fernet_key):
        wi = make_watched_index()
        creds = json.dumps({"webhook_url": "https://discord.com/api/webhooks/test"})
        channel = _make_channel("discord", _encrypt(fernet_key, creds))

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi
        mock_session.execute.return_value.scalars.return_value.all.return_value = [channel]

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx, \
             patch("app.worker.tasks.notify.enricher.get_course_detail", return_value=None), \
             patch("app.worker.tasks.notify.notifier.send_discord", return_value=SendResult(success=True)), \
             patch("app.core.config.settings.FERNET_KEY", fernet_key), \
             patch("app.core.security._fernet", None):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(wi.id), 11643, "12026")

        assert result["status"] == "sent"
        dedup_key = f"sniper:notified:{wi.user_id}:11643:12026"
        assert fake_r.get(dedup_key) == "1"

    def test_sets_dedup_key_even_when_all_fail(self, fake_r, fernet_key):
        # Dedup key is set before delivery so status always reflects reality,
        # even if every channel times out.  Resnipe clears the key to re-enable.
        wi = make_watched_index()
        creds = json.dumps({"webhook_url": "https://discord.com/api/webhooks/test"})
        channel = _make_channel("discord", _encrypt(fernet_key, creds))

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi
        mock_session.execute.return_value.scalars.return_value.all.return_value = [channel]

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx, \
             patch("app.worker.tasks.notify.enricher.get_course_detail", return_value=None), \
             patch("app.worker.tasks.notify.notifier.send_discord", return_value=SendResult(success=False, error="timeout")), \
             patch("app.core.config.settings.FERNET_KEY", fernet_key), \
             patch("app.core.security._fernet", None):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(wi.id), 11643, "12026")

        assert result["status"] == "all_failed"
        dedup_key = f"sniper:notified:{wi.user_id}:11643:12026"
        assert fake_r.get(dedup_key) == "1"


class TestDispatchNotificationGuards:
    def test_skips_inactive_watched_index(self, fake_r, fernet_key):
        wi = make_watched_index(is_active=False)
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(wi.id), 11643, "12026")

        assert result["status"] == "skipped"
        assert result["reason"] == "watched_index_inactive"

    def test_skips_when_watched_index_not_found(self, fake_r):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(uuid.uuid4()), 11643, "12026")

        assert result["status"] == "skipped"

    def test_opens_status_when_no_channels(self, fake_r, fernet_key):
        # Status is still set to opened even when no channels are configured,
        # so the UI shows the course as opened rather than stuck watching.
        wi = make_watched_index()
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            result = dispatch_notification.run(str(wi.id), 11643, "12026")

        assert result["status"] == "opened_no_channels"
        assert result["reason"] == "no_channels"


class TestDispatchNotificationLogging:
    def test_writes_notification_log_on_send(self, fake_r, fernet_key):
        wi = make_watched_index()
        creds = json.dumps({"webhook_url": "https://discord.com/api/webhooks/test"})
        channel = _make_channel("discord", b"encrypted_blob_placeholder")

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = wi
        mock_session.execute.return_value.scalars.return_value.all.return_value = [channel]
        added_rows = []
        mock_session.add.side_effect = added_rows.append

        # Patch decrypt_credential directly — avoids the module-level _fernet cache
        # in security.py which ignores settings.FERNET_KEY patches after first init.
        with patch("app.worker.tasks.notify.get_worker_redis", return_value=fake_r), \
             patch("app.worker.tasks.notify.get_worker_session") as mock_ctx, \
             patch("app.worker.tasks.notify.enricher.get_course_detail", return_value=None), \
             patch("app.worker.tasks.notify.notifier.send_discord", return_value=SendResult(success=True)), \
             patch("app.worker.tasks.notify.decrypt_credential", return_value=creds):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from app.worker.tasks.notify import dispatch_notification
            dispatch_notification.run(str(wi.id), 11643, "12026")

        from app.models.notification_log import NotificationLog
        log_rows = [r for r in added_rows if isinstance(r, NotificationLog)]
        assert len(log_rows) == 1
        assert log_rows[0].event_type == "open_notify"
        assert log_rows[0].delivery_status == "sent"
        assert log_rows[0].channel_type == "discord"
