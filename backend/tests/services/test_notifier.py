"""Tests for notification dispatch helpers.

Security invariant: send_discord and send_pushover must never return a SendResult
whose error field contains the webhook URL, token, or user_key — str(HTTPError)
from requests includes the full request URL, so we verify the sanitisation here.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.notifier import NotificationPayload, SendResult, send_discord, send_pushover

_WEBHOOK = "https://discord.com/api/webhooks/123456789/SECRET_TOKEN_ABCDEF"
_PUSHOVER_TOKEN = "secret_pushover_token"
_PUSHOVER_USER = "secret_user_key"


def _payload() -> NotificationPayload:
    return NotificationPayload(
        index_number=11643,
        semester_code="92026",
        label=None,
        course_detail=None,
        webreg_url="https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection=92026&indexList=11643",
    )


def _http_error(status_code: int, url: str) -> requests.exceptions.HTTPError:
    resp = MagicMock()
    resp.status_code = status_code
    resp.reason = "Bad Request"
    exc = requests.exceptions.HTTPError(
        f"{status_code} Client Error: Bad Request for url: {url}", response=resp
    )
    return exc


class TestSendDiscordErrorSanitisation:
    def test_http_error_does_not_leak_webhook_url(self):
        exc = _http_error(400, _WEBHOOK)
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = exc
            result = send_discord(_WEBHOOK, _payload())

        assert result.success is False
        assert _WEBHOOK not in (result.error or "")
        assert "SECRET_TOKEN_ABCDEF" not in (result.error or "")

    def test_http_error_surfaces_status_code(self):
        exc = _http_error(429, _WEBHOOK)
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = exc
            result = send_discord(_WEBHOOK, _payload())

        assert result.success is False
        assert result.error == "HTTP 429"

    def test_connection_error_surfaces_type_name_not_url(self):
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("conn refused")):
            result = send_discord(_WEBHOOK, _payload())

        assert result.success is False
        assert _WEBHOOK not in (result.error or "")
        assert result.error == "ConnectionError"

    def test_success_returns_no_error(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            result = send_discord(_WEBHOOK, _payload())

        assert result.success is True
        assert result.error is None


class TestSendPushoverErrorSanitisation:
    def test_http_error_does_not_leak_credentials(self):
        pushover_url = "https://api.pushover.net/1/messages.json"
        exc = _http_error(400, pushover_url)
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = exc
            result = send_pushover(_PUSHOVER_TOKEN, _PUSHOVER_USER, _payload())

        assert result.success is False
        assert _PUSHOVER_TOKEN not in (result.error or "")
        assert _PUSHOVER_USER not in (result.error or "")

    def test_http_error_surfaces_status_code(self):
        exc = _http_error(500, "https://api.pushover.net/1/messages.json")
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = exc
            result = send_pushover(_PUSHOVER_TOKEN, _PUSHOVER_USER, _payload())

        assert result.success is False
        assert result.error == "HTTP 500"

    def test_connection_error_surfaces_type_name(self):
        with patch("requests.post", side_effect=requests.exceptions.Timeout("timed out")):
            result = send_pushover(_PUSHOVER_TOKEN, _PUSHOVER_USER, _payload())

        assert result.success is False
        assert result.error == "Timeout"

    def test_success_returns_no_error(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            result = send_pushover(_PUSHOVER_TOKEN, _PUSHOVER_USER, _payload())

        assert result.success is True
        assert result.error is None
