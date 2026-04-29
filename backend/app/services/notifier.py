"""Notification dispatch helpers for Discord and Pushover.

Credentials are passed in explicitly — never read from env, never logged.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from app.services.soc_client import CourseDetail

logger = logging.getLogger(__name__)

_PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
_WEBREG_BASE = "https://sims.rutgers.edu/webreg/editSchedule.htm"


@dataclass
class NotificationPayload:
    index_number: int
    semester_code: str
    label: Optional[str]
    course_detail: Optional[CourseDetail]
    webreg_url: str


@dataclass
class SendResult:
    success: bool
    error: Optional[str] = None


def build_webreg_url(index_number: int, semester_code: str) -> str:
    return f"{_WEBREG_BASE}?login=cas&semesterSelection={semester_code}&indexList={index_number}"


def _format_message(payload: NotificationPayload) -> str:
    lines = [f"🔗 **WebReg Link:** {payload.webreg_url}", ""]
    label_suffix = f" ({payload.label})" if payload.label else ""
    detail = payload.course_detail
    if detail:
        lines.append(f"**Index {payload.index_number}**{label_suffix}")
        lines.append(f"**{detail.subject} {detail.course_number}: {detail.title}**")
        lines.append(f"Section: {detail.section}")
        if detail.instructors:
            lines.append(f"**Instructor(s):** {', '.join(detail.instructors)}")
        if detail.meeting_times:
            lines.append(f"**Meeting Times:** {' | '.join(detail.meeting_times)}")
    else:
        lines.append(f"**Index:** {payload.index_number}{label_suffix}")
        lines.append("_Course details loading..._")
    return "\n".join(lines)


def send_discord(webhook_url: str, payload: NotificationPayload) -> SendResult:
    """POST notification to a Discord webhook URL.

    webhook_url must be the decrypted value from NotificationChannel.credential_blob.
    Never log webhook_url.
    """
    detail = payload.course_detail
    title = (
        f"Index {payload.index_number}: {detail.subject} {detail.course_number}"
        if detail
        else f"Index {payload.index_number} Available"
    )
    body = {
        "content": f"🚨 **INDEX {payload.index_number} IS NOW OPEN!** 🚨",
        "embeds": [{
            "title": title,
            "description": _format_message(payload),
            "color": 0x00FF00,
        }],
    }
    try:
        resp = requests.post(webhook_url, json=body, timeout=10)
        resp.raise_for_status()
        return SendResult(success=True)
    except requests.exceptions.RequestException as exc:
        return SendResult(success=False, error=str(exc))


def send_pushover(token: str, user_key: str, payload: NotificationPayload) -> SendResult:
    """POST notification to the Pushover API.

    token/user_key must be the decrypted values from NotificationChannel.credential_blob.
    Never log token or user_key.
    """
    body = {
        "token": token,
        "user": user_key,
        "title": f"Index {payload.index_number} Available",
        "message": _format_message(payload),
        "priority": 1,
        "url": payload.webreg_url,
        "url_title": "Open WebReg",
    }
    try:
        resp = requests.post(_PUSHOVER_URL, data=body, timeout=10)
        resp.raise_for_status()
        return SendResult(success=True)
    except requests.exceptions.RequestException as exc:
        return SendResult(success=False, error=str(exc))
