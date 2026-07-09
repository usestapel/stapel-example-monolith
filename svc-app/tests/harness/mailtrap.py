"""File mailtrap: an email backend that writes each message to var/mailtrap/
as a machine-readable JSON file, plus read/clear helpers for tests and dev.

Point EMAIL_BACKEND at FileMailtrapBackend to make outbound mail inspectable
without a real SMTP server — the observable effect an async-consumer test
asserts on (system-design §7.21).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


def mailtrap_dir() -> Path:
    configured = getattr(settings, "MAILTRAP_DIR", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "var" / "mailtrap"


class FileMailtrapBackend(BaseEmailBackend):
    """Write each EmailMessage to var/mailtrap/<ns>.json."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        directory = mailtrap_dir()
        directory.mkdir(parents=True, exist_ok=True)
        written = 0
        for index, message in enumerate(email_messages):
            record = {
                "subject": message.subject,
                "from": message.from_email,
                "to": list(message.to),
                "cc": list(message.cc),
                "bcc": list(message.bcc),
                "reply_to": list(message.reply_to),
                "body": message.body,
                "content_subtype": message.content_subtype,
                "alternatives": [
                    {"content": content, "mimetype": mimetype}
                    for content, mimetype in getattr(message, "alternatives", []) or []
                ],
                "headers": dict(message.extra_headers or {}),
            }
            name = f"{time.time_ns()}-{index:03d}.json"
            (directory / name).write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            written += 1
        return written


def read_mailtrap() -> list[dict]:
    """Return all trapped messages, oldest first (sorted by filename)."""
    directory = mailtrap_dir()
    if not directory.exists():
        return []
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    ]


def clear_mailtrap() -> None:
    """Delete every trapped message. Safe when the directory is absent."""
    directory = mailtrap_dir()
    if not directory.exists():
        return
    for path in directory.glob("*.json"):
        path.unlink()
