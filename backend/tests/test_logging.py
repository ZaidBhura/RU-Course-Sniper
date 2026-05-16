"""Unit tests for the structlog logging configuration.

These tests verify:
- SecretScrubber redacts sensitive keys
- Non-sensitive keys pass through unchanged
- configure_logging() runs without error (smoke test)
"""

from app.core.logging import _scrub_secrets, configure_logging


def test_scrub_password():
    event = {"event": "user.login", "password": "hunter2", "email": "x@x.com"}
    result = _scrub_secrets(None, "info", event)
    assert result["password"] == "[REDACTED]"
    assert result["email"] == "x@x.com"


def test_scrub_token():
    event = {"event": "token.check", "token": "eyJhbGciOiJIUzI1NiJ9.secret"}
    result = _scrub_secrets(None, "info", event)
    assert result["token"] == "[REDACTED]"


def test_scrub_access_token():
    event = {"event": "auth", "access_token": "abc123", "user_id": "u-1"}
    result = _scrub_secrets(None, "info", event)
    assert result["access_token"] == "[REDACTED]"
    assert result["user_id"] == "u-1"


def test_scrub_webhook_url():
    event = {"event": "notify", "webhook_url": "https://discord.com/api/webhooks/x/y"}
    result = _scrub_secrets(None, "info", event)
    assert result["webhook_url"] == "[REDACTED]"


def test_scrub_fernet_key():
    event = {"event": "startup", "fernet_key": "abc="}
    result = _scrub_secrets(None, "info", event)
    assert result["fernet_key"] == "[REDACTED]"


def test_non_sensitive_keys_unchanged():
    event = {
        "event": "poll_soc.complete",
        "semester_code": "92026",
        "total_open": 42,
        "newly_open": 3,
    }
    result = _scrub_secrets(None, "info", dict(event))
    assert result == event


def test_configure_logging_smoke():
    configure_logging(dev=True)
    import structlog
    log = structlog.get_logger("test")
    log.info("smoke_test", key="value")
