"""wait_for — poll a condition until it holds, instead of sleeping blindly.

For genuinely asynchronous effects (a broker round-trip, a background worker).
For the in-process outbox prefer drain_outbox(), which is fully deterministic
and needs no waiting at all (system-design §7.21: no sleeps in tests).
"""
from __future__ import annotations

import time
from collections.abc import Callable


class WaitTimeout(AssertionError):
    """Raised when wait_for's condition stays falsy past the timeout."""


def wait_for(
    condition: Callable[[], object],
    timeout: float = 2.0,
    interval: float = 0.01,
    message: str | None = None,
):
    """Call condition() until it returns a truthy value; return that value.

    Raises WaitTimeout after ``timeout`` seconds. ``interval`` is the poll gap.
    """
    deadline = time.monotonic() + timeout
    while True:
        value = condition()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise WaitTimeout(message or f"condition not met within {timeout}s")
        time.sleep(interval)
