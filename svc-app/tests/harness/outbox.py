"""drain_outbox — synchronously deliver pending outbox rows in tests.

The production relay (``manage.py dispatch_outbox``) runs continuously; in
tests we drain on demand so an async flow splits into synchronous halves:
emit writes a row (producer), drain delivers it to its observable effect
(consumer) — system-design §7.21.
"""
from __future__ import annotations


def drain_outbox(max_passes: int = 100) -> int:
    """Deliver every pending outbox row through the real delivery path
    (stapel_core.django.outbox.relay.dispatch_pending). Returns rows delivered.

    Rows are forced due first so retry backoff never makes a test wait; loops
    until the outbox is empty or a row stops making progress (permanent fail).
    """
    from django.utils import timezone
    from stapel_core.django.outbox.models import OutboxEvent
    from stapel_core.django.outbox.relay import dispatch_pending

    delivered_total = 0
    for _ in range(max_passes):
        pending = OutboxEvent.objects.filter(dispatched_at__isnull=True)
        if not pending.exists():
            break
        pending.update(next_attempt_at=timezone.now())
        delivered, _failed = dispatch_pending(limit=1000)
        delivered_total += delivered
        if delivered == 0:
            break
    return delivered_total
