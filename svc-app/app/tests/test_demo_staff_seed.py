"""Demo staff seed — bootstrap wiring (admin-suite AS-7, CAT-3 pattern).

Pins the contract ``bootstrap.sh`` relies on, mirroring the catalog seed:
a clean DB + ``seed_demo_staff --seed-if-empty`` materializes one staff user
per admin-suite role; a second bootstrap pass is a pure no-op; the roles land
through the auth service's single write path so the ``staff_roles`` field is
materialized and every mandate role source sees them.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from app.management.commands.seed_demo_staff import DEMO_STAFF

User = get_user_model()

EXPECTED = {username: role for username, _, role in DEMO_STAFF}


@pytest.mark.django_db
class TestDemoStaffSeed:
    def test_seed_creates_one_staff_user_per_role(self):
        assert not User.objects.filter(username__in=EXPECTED).exists()

        call_command("seed_demo_staff", "--seed-if-empty")

        for username, role in EXPECTED.items():
            user = User.objects.get(username=username)
            assert user.is_staff
            assert not user.is_superuser          # A5: demos live inside the mandate
            # assignment table (auth single-writer) and the materialized field agree
            assert list(
                user.staff_role_assignments.values_list("role_name", flat=True)
            ) == [role]
            assert user.staff_roles == [role]

    def test_seed_if_empty_is_a_no_op_on_second_run(self):
        call_command("seed_demo_staff", "--seed-if-empty")
        before = list(
            User.objects.filter(username__in=EXPECTED)
            .values_list("username", "staff_roles")
            .order_by("username")
        )

        call_command("seed_demo_staff", "--seed-if-empty")

        after = list(
            User.objects.filter(username__in=EXPECTED)
            .values_list("username", "staff_roles")
            .order_by("username")
        )
        assert after == before
        assert User.objects.filter(username__in=EXPECTED).count() == len(EXPECTED)

    def test_seeded_roles_engage_the_mandate(self):
        """End-to-end: the seeded editor really can change but not delete."""
        call_command("seed_demo_staff", "--seed-if-empty")
        editor = User.objects.get(username="demo-editor")
        assert editor.has_perm("billing.change_wallet")
        assert not editor.has_perm("billing.delete_wallet")
