import pytest

from tests.harness import clear_mailtrap, read_mailtrap
from tests.harness import drain_outbox as _drain_outbox


@pytest.fixture(autouse=True)
def _reset_comm_registries():
    """Isolate action subscribers between tests (the registry is process-global)."""
    from stapel_core.comm import action_registry, function_registry

    action_registry.clear()
    function_registry.clear()
    yield
    action_registry.clear()
    function_registry.clear()


@pytest.fixture(autouse=True)
def outbox_comm(settings):
    """Run comm in-process with the transactional outbox ENABLED against the
    test DB — the production delivery path (emit -> outbox row -> dispatch),
    so producer/consumer/atomicity assertions exercise real behaviour."""
    settings.STAPEL_COMM = {
        **getattr(settings, "STAPEL_COMM", {}),
        "OUTBOX_ENABLED": True,
        "ACTION_TRANSPORT": "inprocess",
    }


@pytest.fixture
def drain_outbox():
    """Synchronously flush pending outbox rows through delivery (the test-time
    stand-in for ``manage.py dispatch_outbox``). Returns rows delivered."""
    return _drain_outbox


@pytest.fixture
def mailtrap(settings):
    """File mailtrap: force the file email backend, clear var/mailtrap/, then
    yield read_mailtrap(). pytest-django swaps EMAIL_BACKEND to locmem by
    default; async-consumer tests assert on the on-disk trap instead."""
    settings.EMAIL_BACKEND = "tests.harness.mailtrap.FileMailtrapBackend"
    clear_mailtrap()
    yield read_mailtrap
    clear_mailtrap()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()
