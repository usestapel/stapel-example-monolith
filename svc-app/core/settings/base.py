"""Django settings for svc-app service."""
from stapel_core.django.settings import *  # type: ignore  # noqa
import os
from pathlib import Path

SERVICE_NAME = "Stapel Example Monolith"
# Monolith serves from the root; each module mounts its natural prefix in urls.py
URL_PREFIX = ""
CSRF_COOKIE_NAME = "csrftoken_app"
SESSION_COOKIE_NAME = "stapel_sid_app"
BASE_DIR = Path(__file__).resolve().parent.parent.parent

with open(BASE_DIR / "version.txt") as v_file:
    APP_VERSION_NUMBER = v_file.read().strip()

STATIC_ROOT = f"/app/staticfiles/app/"
STATIC_URL = f"/staticfiles/app/"
STATICFILES_DIRS = get_staticfiles_dirs(BASE_DIR)
MEDIA_ROOT = f"/app/media/app/"
MEDIA_URL = f"/media/app/"

# Dev fallbacks live in dev.py; prod.py refuses to start without real values.
SECRET_KEY = os.getenv("SECRET_KEY", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
ALLOWED_HOSTS = ALLOWED_HOSTS + ["svc-app"]  # type: ignore[name-defined]

# Prefix of the dedicated auth service (e.g. "auth") when running in a
# multi-service stack. Empty (the monolith default) = no external auth
# service: LOGIN_URL/LOGOUT_REDIRECT_URL derive to this instance's own
# reverse("admin:login") via the stapel_core mount registry, so they follow
# any prefix the deployment mounts the whole project under.
STAPEL_AUTH_SERVICE_PREFIX = os.getenv("STAPEL_AUTH_SERVICE_PREFIX", "")

INSTALLED_APPS = COMMON_INSTALLED_APPS + [
    "stapel_auth",
    "stapel_gdpr",
    "stapel_profiles",
    "stapel_notifications",
    "stapel_workspaces",
    "stapel_billing",
    "stapel_cdn",
    "stapel_translate",
    # django-treenode registers the tree-cache signals its AppConfig.ready()
    # wires up (required for stapel_categories' tn_* fields) — must be
    # installed alongside stapel_categories, not just pip-resolved as its
    # transitive dependency.
    "treenode",
    "stapel_categories",
    "app",
]

MIDDLEWARE = COMMON_MIDDLEWARE

ROOT_URLCONF = "core.urls"
TEMPLATES = get_common_templates(BASE_DIR)
WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": get_default_database("stapel_app"),
}

CACHES = {
    "default": {
        **DEFAULT_CACHE,
        "KEY_PREFIX": "app",
    }
}

# URL *name*, not a hardcoded path (house convention: absolute paths break
# under a mount prefix; Django's resolve_url() reverses names lazily).
LOGIN_REDIRECT_URL = "admin:index"
AUTH_USER_MODEL = "users.User"

# =============================================================================
# ADMIN SUITE — the staff mandate, wired end to end (docs/admin-suite.md, AS-7)
# =============================================================================
# This monolith is the live reference for the admin suite: staff rights are a
# *computed function* of (model @access declaration × role clearance), never
# rows piled into auth_permission. The three moving parts below are all a host
# project ever configures — declarations live on the models in the libraries.

# 1. The backend chain. MandateBackend is the MAC half (grants strictly by
#    declaration × clearance); AuditedModelBackend is the DAC overlay (a plain
#    ModelBackend that still honors manual grants, but logs + signals any grant
#    used *above* the mandate — set STAPEL_ACCESS["STRICT"]=True to deny those
#    instead). Replacing the default single ModelBackend with this pair is the
#    whole opt-in: with no roles assigned the chain behaves exactly like stock
#    Django (superuser everything, staff by manual grants).
AUTHENTICATION_BACKENDS = [
    "stapel_core.access.backend.MandateBackend",
    "stapel_core.access.backend.AuditedModelBackend",
]

# 2. Role definitions (name → clearance profile) — deploy config, identical
#    across every service of a deployment; assignments (user → roles) live in
#    the auth service. The builtins viewer(LOW)/editor(MID)/admin(HIGH) come
#    for free; we add a domain-scoped custom role to show the shape: an
#    "accountant" is LOW-clearance everywhere but HIGH inside billing, so it can
#    fully manage wallets/transactions without any reach into other apps.
#    NB: the scope key is the app *label* ("billing"), not the package name.
STAPEL_ACCESS = {
    "ROLES": {
        "accountant": {"clearance": "low", "apps": {"billing": "high"}},
    },
    # The monolith hosts its own auth, so read roles straight from the
    # assignment table first (freshest — a revocation lands on the next
    # request, no token refresh needed), then fall through the standard
    # claim → local-field → role:* group chain used by remote services.
    "ROLE_SOURCES": [
        "stapel_auth.staff_roles.assignment_roles",
        "stapel_core.access.sources.claim_roles",
        "stapel_core.access.sources.user_field_roles",
        "stapel_core.access.sources.group_roles",
    ],
    # Step-up on HIGH operations (delete in the standard preset) is ON by
    # default — stapel-auth registers OTP/TOTP/passkey factors, so the gate is
    # live here (it self-disables only where no factor exists, e.g. the minimal
    # example). Left implicit; override STAPEL_ACCESS["STEP_UP"] to tune.
}

# 3. Admin visibility. SHOW_OPS_MODELS is the only knob a host usually flips:
#    ops journals (outbox/taskstore/eventstore/StripeWebhookEvent…) stay hidden
#    from staff and superuser-read-only by default; turning it on lets any staff
#    *view* them (still read-only) — handy in dev. It is env-readable
#    (SHOW_OPS_MODELS=true in .env for dev), unlike the trust-shaping ACCESS
#    keys, so no settings edit is needed to toggle it per environment.
# (No STAPEL_ADMIN block is required: SHOW_OPS_MODELS resolves from the env,
#  and MODELS/NAV_LINKS default empty. Add STAPEL_ADMIN here to override.)

FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_DEFAULT_QUEUE = "app"

from stapel_core.django.openapi.swagger import get_spectacular_settings
SPECTACULAR_SETTINGS = get_spectacular_settings(
    title="Stapel Example Monolith API",
    description="Stapel Example Monolith service API",
    version="1.0.0",
)
