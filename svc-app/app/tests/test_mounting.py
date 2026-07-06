"""Monolith mounting — the anonymous→login→next→target chain must survive
any mount prefix (arch-monolith-mounting).

The live bug this pins down: a project mounted whole under a prefix
(``/stapel-studio/...``) redirected anonymous admin visitors to the
root-relative ``/admin/login/`` and then to ``/auth/admin/login/`` — both
404 in that deployment. LOGIN_URL and every cross-module target must be
*derived* from the URLconf/mount registry, never hardcoded root-relative.
"""
import pytest
from django.test import Client
from django.urls import reverse

PREFIXED_URLCONF = "app.tests.urls_prefixed"


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        username="root", email="root@example.com", password="s3cret-pass"
    )


@pytest.fixture
def prefixed(settings):
    settings.ROOT_URLCONF = PREFIXED_URLCONF


def _follow_login_chain(client, entry_path, password="s3cret-pass"):
    """Anonymous entry → login redirect → POST credentials → next target."""
    # 1. anonymous hit on a protected admin page
    resp = client.get(entry_path)
    assert resp.status_code == 302, f"expected redirect from {entry_path}"
    login_url = resp["Location"]
    # the login target must live inside the same deployment (same prefix)
    prefix = entry_path.split("/admin/")[0]
    assert login_url.startswith(f"{prefix}/admin/login/"), login_url
    assert f"next={entry_path.replace('/', '%2F')}" in login_url

    # 2. the login page actually exists (this was the 404 in the live bug)
    resp = client.get(login_url)
    assert resp.status_code == 200

    # 3. POST credentials — must land back on the originally requested page
    path, _, query = login_url.partition("?")
    next_target = query.removeprefix("next=").replace("%2F", "/")
    resp = client.post(
        path + "?" + query,
        {"username": "root", "password": password, "next": next_target},
    )
    assert resp.status_code == 302
    assert resp["Location"] == next_target
    resp = client.get(resp["Location"])
    assert resp.status_code == 200
    return resp


@pytest.mark.django_db
class TestLoginChainAtRoot:
    """Regression: the historical root mount keeps working unchanged."""

    def test_admin_chain(self, admin_user):
        _follow_login_chain(Client(), "/admin/")

    def test_login_redirect_url_is_reversible(self):
        from django.conf import settings as dj_settings
        from django.shortcuts import resolve_url

        assert resolve_url(dj_settings.LOGIN_REDIRECT_URL) == reverse("admin:index")


@pytest.mark.django_db
class TestLoginChainUnderPrefix:
    """The stapel-studio shape: whole project under /stapel-studio/."""

    def test_admin_chain_stays_inside_prefix(self, prefixed, admin_user):
        _follow_login_chain(Client(), "/stapel-studio/admin/")

    def test_derived_login_url_carries_prefix(self, prefixed):
        from stapel_core.django.mounts import admin_login_url

        assert admin_login_url() == "/stapel-studio/admin/login/"

    def test_login_without_next_lands_on_prefixed_admin(self, prefixed, admin_user):
        client = Client()
        resp = client.post(
            "/stapel-studio/admin/login/",
            {"username": "root", "password": "s3cret-pass"},
        )
        assert resp.status_code == 302
        # LOGIN_REDIRECT_URL = "admin:index" reverses inside the prefix
        assert resp["Location"] == "/stapel-studio/admin/"


class TestSystemCheck:
    """E-level check: unresolvable LOGIN_URL fails the deploy, not the user."""

    def test_monolith_defaults_are_clean(self):
        from stapel_core.django.checks import check_auth_redirect_settings

        assert check_auth_redirect_settings() == []

    def test_derived_settings_survive_prefix_mount(self, prefixed):
        from stapel_core.django.checks import check_auth_redirect_settings

        assert check_auth_redirect_settings() == []

    def test_hardcoded_root_login_url_is_loud_error(self, prefixed, settings):
        from stapel_core.django.checks import (
            E001_LOGIN_URL_UNRESOLVABLE,
            check_auth_redirect_settings,
        )

        settings.LOGIN_URL = "/admin/login/"
        ids = [f.id for f in check_auth_redirect_settings()]
        assert E001_LOGIN_URL_UNRESOLVABLE in ids
