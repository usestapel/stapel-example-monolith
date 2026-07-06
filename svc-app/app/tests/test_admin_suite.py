"""Admin-suite smoke matrix — the mandate, wired live (docs/admin-suite.md).

Pins the behavior the monolith settings promise: the ``@access`` declarations
on the library models, crossed with the role clearances in
``STAPEL_ACCESS["ROLES"]``, produce exactly the right allow/deny grid — with no
rows in ``auth_permission``. Two surfaces are exercised:

- the **mandate matrix** via ``user.has_perm`` (what the MandateBackend
  computes: declaration × clearance, per-app scope included);
- the **admin client** via Django's test ``Client`` (what a logged-in staff
  user actually sees at ``/admin/`` — ops journals hidden, direct URLs closed).

Models used (all from installed libraries, no fixtures needed):
- ``billing.wallet`` — business, standard: view LOW / add·change MID / delete HIGH.
- ``categories.category`` — business, standard (undecorated → the implicit default).
- ``stapel_outbox.outboxevent`` — ops: view HIGH, mutations forbidden.

Roles under test come from ``core.settings.base``: builtins viewer(LOW) /
editor(MID) / admin(HIGH) + the custom ``accountant`` (LOW everywhere, HIGH in
billing).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

WALLET = "billing.{}_wallet"
CATEGORY = "categories.{}_category"
OUTBOX = "stapel_outbox.{}_outboxevent"


def _staff(username, role=None, *, superuser=False):
    from stapel_auth.staff_roles import assign_staff_role

    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="pw-1234",
        is_staff=True,
    )
    if superuser:
        user.is_superuser = True
        user.save(update_fields=["is_superuser"])
    if role:
        assign_staff_role(user, role)
    return user


# ── Role definitions resolve from settings ──────────────────────────────────


@pytest.mark.django_db
class TestRoleRegistry:
    def test_settings_roles_merge_over_builtins(self):
        from stapel_core.access import effective_roles

        roles = effective_roles()
        # builtins survive, the custom scoped role is present
        assert set(roles) >= {"viewer", "editor", "admin", "accountant"}
        accountant = roles["accountant"]
        assert accountant.clearance_for(None).name == "LOW"
        assert accountant.clearance_for("billing").name == "HIGH"

    def test_system_checks_are_clean(self):
        """No E-level access/admin/nav config errors with the shipped settings."""
        from django.core.management import call_command

        # Raises SystemCheckError on any Error-level finding.
        call_command("check")


# ── The mandate matrix (has_perm) ───────────────────────────────────────────


@pytest.mark.django_db
class TestMandateMatrix:
    def test_viewer_reads_business_only(self):
        viewer = _staff("m-viewer", "viewer")
        assert viewer.has_perm(WALLET.format("view"))       # LOW ≥ LOW
        assert not viewer.has_perm(WALLET.format("change"))  # MID > LOW
        assert not viewer.has_perm(WALLET.format("delete"))  # HIGH > LOW
        assert not viewer.has_perm(OUTBOX.format("view"))    # ops: HIGH > LOW

    def test_editor_mutates_but_never_deletes(self):
        editor = _staff("m-editor", "editor")
        assert editor.has_perm(WALLET.format("view"))
        assert editor.has_perm(WALLET.format("change"))     # MID ≥ MID
        assert editor.has_perm(WALLET.format("add"))
        assert not editor.has_perm(WALLET.format("delete"))  # HIGH > MID

    def test_admin_holds_the_full_mandate(self):
        admin = _staff("m-admin", "admin")
        assert admin.has_perm(WALLET.format("view"))
        assert admin.has_perm(WALLET.format("change"))
        assert admin.has_perm(WALLET.format("delete"))       # HIGH ≥ HIGH
        # ops is still superuser-only at the mandate level (HIGH view is met,
        # but the ops read-only contract is imposed by StapelModelAdmin, tested
        # separately). At the pure-mandate layer, admin meets outbox view:
        assert admin.has_perm(OUTBOX.format("view"))

    def test_accountant_scope_is_billing_only(self):
        acc = _staff("m-acc", "accountant")
        # HIGH inside billing → full CRUD on wallets
        assert acc.has_perm(WALLET.format("view"))
        assert acc.has_perm(WALLET.format("change"))
        assert acc.has_perm(WALLET.format("delete"))         # billing HIGH
        # LOW everywhere else → read a category, but never delete it
        assert acc.has_perm(CATEGORY.format("view"))         # LOW ≥ LOW
        assert not acc.has_perm(CATEGORY.format("change"))   # MID > LOW
        assert not acc.has_perm(CATEGORY.format("delete"))   # HIGH > LOW

    def test_unassigned_staff_gets_nothing(self):
        """Opt-in by first role: a staff user with no role holds no mandate."""
        nobody = _staff("m-nobody")
        assert not nobody.has_perm(WALLET.format("view"))
        assert not nobody.has_perm(CATEGORY.format("view"))


# ── Ops visibility through the real admin client ─────────────────────────────


@pytest.mark.django_db
class TestOpsVisibilityViaAdminClient:
    def _login(self, user):
        client = Client()
        # Two backends are configured, so force_login needs an explicit one;
        # AuditedModelBackend is the ModelBackend half that carries get_user
        # (MandateBackend is authorization-only).
        client.force_login(
            user, backend="stapel_core.access.backend.AuditedModelBackend"
        )
        return client

    def test_viewer_cannot_reach_ops_changelist(self, settings):
        settings.STAPEL_ADMIN = {"SHOW_OPS_MODELS": False}
        viewer = _staff("c-viewer", "viewer")
        resp = self._login(viewer).get("/admin/stapel_outbox/outboxevent/")
        # No view permission → admin returns 403 (direct URL closed, not just
        # filtered from the index).
        assert resp.status_code == 403

    def test_viewer_sees_business_changelist(self, settings):
        settings.STAPEL_ADMIN = {"SHOW_OPS_MODELS": False}
        viewer = _staff("c-viewer2", "viewer")
        resp = self._login(viewer).get("/admin/billing/wallet/")
        assert resp.status_code == 200

    def test_show_ops_models_lets_staff_view_readonly(self, settings):
        settings.STAPEL_ADMIN = {"SHOW_OPS_MODELS": True}
        viewer = _staff("c-viewer3", "viewer")
        client = self._login(viewer)
        resp = client.get("/admin/stapel_outbox/outboxevent/")
        assert resp.status_code == 200          # dev mode: visible…
        # …but read-only — adding is still forbidden by the ops declaration.
        assert client.get("/admin/stapel_outbox/outboxevent/add/").status_code == 403

    def test_ops_stays_readonly_even_for_superuser(self, settings):
        settings.STAPEL_ADMIN = {"SHOW_OPS_MODELS": False}
        root = _staff("c-root", superuser=True)
        client = self._login(root)
        assert client.get("/admin/stapel_outbox/outboxevent/").status_code == 200
        # superuser bypasses the mandate (A5) but the ops read-only contract is
        # re-imposed at the admin layer — no add view.
        assert client.get("/admin/stapel_outbox/outboxevent/add/").status_code == 403


# ── Step-up on HIGH delete: actual behavior in this deployment ───────────────


@pytest.mark.django_db
class TestStepUpOnDelete:
    """stapel-auth is installed here, so verification factors are registered
    and step-up is *active* (not degraded). Delete (HIGH) therefore needs a
    fresh grant on top of the mandate — but ONLY through ``StapelModelAdmin``:
    the gate lives at the admin layer, not in the backend. A plain
    ``admin.ModelAdmin`` (like the registered ``WalletAdmin``) still gets full
    mandate *visibility* enforcement, but no step-up — that trade-off is
    pinned below so the example documents the real behavior.
    """

    def _stapel_wallet_admin(self):
        """A StapelModelAdmin over Wallet — the step-up-enforcing admin class."""
        from django.contrib import admin

        from stapel_billing.models import Wallet
        from stapel_core.django.admin.base import StapelModelAdmin

        return StapelModelAdmin(Wallet, admin.site)

    def _request(self, user):
        from django.test import RequestFactory

        req = RequestFactory().get("/admin/billing/wallet/")
        req.user = user
        return req

    def test_step_up_is_active_not_degraded(self):
        from stapel_core.access.stepup import step_up_active, step_up_capable

        assert step_up_capable()   # stapel-auth registered OTP/TOTP/passkey
        assert step_up_active()    # ENFORCE default True × capable

    def test_admin_delete_blocked_without_fresh_factor(self):
        """admin has the mandate for delete, but step-up gates it: denied."""
        admin_user = _staff("s-admin", "admin")
        wallet_admin = self._stapel_wallet_admin()
        req = self._request(admin_user)
        assert wallet_admin.has_change_permission(req)      # MID, not gated
        assert not wallet_admin.has_delete_permission(req)  # HIGH, step-up gate

    def test_admin_delete_allowed_after_step_up(self):
        """A fresh verification grant for the step-up scope unlocks delete."""
        from stapel_core.access.stepup import step_up_config
        from stapel_core.verification.grants import grant_verification

        admin_user = _staff("s-admin2", "admin")
        cfg = step_up_config()
        grant_verification(
            user_id=str(admin_user.pk), scope=cfg["SCOPE"], max_age=cfg["MAX_AGE"]
        )
        wallet_admin = self._stapel_wallet_admin()
        assert wallet_admin.has_delete_permission(self._request(admin_user))

    def test_editor_delete_denied_by_mandate_before_step_up(self):
        """editor is stopped by the mandate itself (MID < HIGH) — step-up never
        even applies. The 403 an editor sees on delete is a clearance denial,
        not a step-up prompt."""
        editor = _staff("s-editor", "editor")
        wallet_admin = self._stapel_wallet_admin()
        assert not wallet_admin.has_delete_permission(self._request(editor))

    def test_plain_modeladmin_does_not_gate_step_up(self):
        """Documented trade-off: the registered ``WalletAdmin`` subclasses the
        plain ``admin.ModelAdmin``, so the mandate governs it (visibility and
        CRUD by clearance, via the backend) but the step-up gate does NOT
        apply — an admin-role user deletes there without a fresh factor.
        Switching a ModelAdmin's base to StapelModelAdmin is what turns the
        gate on (migration doc, step 4)."""
        from django.contrib import admin as dj_admin

        from stapel_billing.models import Wallet
        from stapel_core.django.admin.base import StapelModelAdmin

        registered = dj_admin.site._registry[Wallet]
        assert not isinstance(registered, StapelModelAdmin)
        admin_user = _staff("s-admin3", "admin")
        # No verification grant issued — plain ModelAdmin still allows delete
        # because the mandate (HIGH ≥ HIGH) is the only check it consults.
        assert registered.has_delete_permission(self._request(admin_user))
