"""Seed demo staff accounts, one per admin-suite role (docs/admin-suite.md).

The monolith ships four demo staff users so the mandate is explorable the
moment the stack is up — each holds exactly one role from
``STAPEL_ACCESS["ROLES"]`` (the three builtins + the custom ``accountant``):

    demo-viewer      viewer      LOW   — read-only across business models
    demo-editor      editor      MID   — add/change, but no delete (HIGH)
    demo-admin       admin       HIGH  — full CRUD (delete still needs step-up)
    demo-accountant  accountant  LOW / billing:HIGH — full reach in billing only

None is a superuser: the whole point is to *see* the mandate, and a superuser
is outside it (invariant A5). Assignment goes through the auth service's only
write path (``assign_staff_role`` — invariant A2), which validates the role
name against the registry and materializes the ``staff_roles`` field + audit
event in one transaction.

Idempotent, mirroring the catalog seed (CAT-3, ``load_catalog --seed-if-empty``):
``--seed-if-empty`` short-circuits when any demo user already exists, and even
without the flag every step is get-or-create / idempotent-assign, so a re-run
writes nothing new.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

#: (username, email, role_name). Kept in sync with STAPEL_ACCESS["ROLES"].
DEMO_STAFF = (
    ("demo-viewer", "demo-viewer@example.com", "viewer"),
    ("demo-editor", "demo-editor@example.com", "editor"),
    ("demo-admin", "demo-admin@example.com", "admin"),
    ("demo-accountant", "demo-accountant@example.com", "accountant"),
)

#: Shared demo password — dev fixtures only, never a real deployment.
DEMO_PASSWORD = "demo-pass-1234"


class Command(BaseCommand):
    help = "Seed demo staff users (one per admin-suite role) — idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-if-empty",
            action="store_true",
            help="Skip entirely if any demo staff user already exists "
            "(bootstrap-safe, mirrors load_catalog --seed-if-empty).",
        )

    def handle(self, *args, **options):
        from stapel_auth.staff_roles import assign_staff_role

        User = get_user_model()
        usernames = [u for u, _, _ in DEMO_STAFF]

        if options["seed_if_empty"] and User.objects.filter(
            username__in=usernames
        ).exists():
            self.stdout.write(
                self.style.WARNING("Demo staff already present — skipping seed.")
            )
            return

        created_users = 0
        assigned_roles = 0
        for username, email, role in DEMO_STAFF:
            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": email, "is_staff": True, "is_active": True},
                )
                if created:
                    user.set_password(DEMO_PASSWORD)
                    user.save(update_fields=["password"])
                    created_users += 1
                elif not user.is_staff:
                    # A pre-existing non-staff account with this name — make it
                    # staff so the role is not a dormant privilege (assign_staff_role
                    # refuses non-staff targets by design).
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])
                _, role_created = assign_staff_role(user, role)
                if role_created:
                    assigned_roles += 1
            self.stdout.write(f"  {username}: role {role!r} ({'new' if created else 'exists'})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo staff ready: {created_users} user(s) created, "
                f"{assigned_roles} role(s) assigned "
                f"(password for all: {DEMO_PASSWORD!r})."
            )
        )
