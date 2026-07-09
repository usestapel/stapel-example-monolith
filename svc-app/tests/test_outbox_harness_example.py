"""Example: the transactional-outbox test pattern (system-design §7.21).

An async flow is split into synchronous, deterministic halves:
  * producer  — an action emitted inside a DB transaction becomes an outbox row
  * consumer  — draining the outbox runs the row through delivery to its effect
  * atomicity — a rolled-back transaction leaves NO row (events never lie about
                state that did not commit)

Copy this pattern for real action/consumer pairs; delete this file once the
suite has its own outbox tests. It exists to prove the harness is wired.
"""
import pytest
from django.db import transaction
from stapel_core.comm import emit, subscribe_action
from stapel_core.django.outbox.models import OutboxEvent


@pytest.mark.django_db
def test_producer_emit_inside_transaction_writes_outbox_row():
    with transaction.atomic():
        emit("harness.ping", {"n": 1})
    # django_db suppresses on_commit, so the row stays pending — proof the event
    # was persisted transactionally rather than delivered eagerly.
    row = OutboxEvent.objects.get()
    assert row.topic == "harness.ping"
    assert row.dispatched_at is None


@pytest.mark.django_db
def test_consumer_drain_delivers_event_to_subscriber(drain_outbox):
    received = []
    subscribe_action("harness.ping", lambda event: received.append(event.payload))

    with transaction.atomic():
        emit("harness.ping", {"n": 2})
    assert received == []  # not delivered until the outbox drains

    delivered = drain_outbox()
    assert delivered == 1
    assert received == [{"n": 2}]


@pytest.mark.django_db
def test_rolled_back_transaction_writes_no_outbox_row():
    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with transaction.atomic():
            emit("harness.ping", {"n": 3})
            raise Boom
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_consumer_side_effect_lands_in_file_mailtrap(drain_outbox, mailtrap):
    from django.core.mail import send_mail

    def send_welcome(event):
        send_mail(
            "Welcome",
            f"Hi {event.payload['name']}",
            "noreply@example.com",
            ["user@example.com"],
        )

    subscribe_action("harness.welcome", send_welcome)

    with transaction.atomic():
        emit("harness.welcome", {"name": "Ada"})
    assert mailtrap() == []  # no mail until the outbox drains

    drain_outbox()

    messages = mailtrap()
    assert len(messages) == 1
    assert messages[0]["subject"] == "Welcome"
    assert messages[0]["to"] == ["user@example.com"]
    assert "Ada" in messages[0]["body"]
