"""Django settings for svc-app service."""
from stapel_core.django.settings import *  # type: ignore  # noqa
import os
from pathlib import Path

SERVICE_NAME = "Stapel Example Monolith"
# Root-mounted: this monolith mounts every feature module on its OWN natural
# prefix (see config/urls.py: /auth/api/, /workspaces/api/, …), exactly the
# paths each module would occupy as a standalone microservice — so a project
# can split into services later without breaking clients, and the emitted
# codegen aggregate carries the same per-module slices the modules emit
# themselves. Hence no service-level URL prefix here.
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
# multi-service stack. Leave empty to use Django's own admin login. Canonical
# name (read by stapel_core.django.mounts / AdminLoginRedirectMiddleware) —
# do not rename without updating both sides.
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
    "stapel_categories",
    "apps.app",
]

MIDDLEWARE = COMMON_MIDDLEWARE

ROOT_URLCONF = "config.urls"
TEMPLATES = get_common_templates(BASE_DIR)
WSGI_APPLICATION = "config.wsgi.application"

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

# Whose users these are, said out loud (stapel-config-lint CFG007). This
# service mounts stapel_auth: it MINTS the tokens and owns the user table,
# so a row is never materialised from somebody else's token. stapel-core
# 0.34 flipped the default to False, which is the value an issuer wants —
# but a security-shaped default is not a declaration, and the linter is
# right that the answer must be in the settings module rather than in
# whatever the installed core happens to default to this release.
JWT_CREATE_USERS_FROM_TOKEN = False

FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

# Inter-module communication (see docs: module-communication.md).
# Action/Function transports follow the project's broker choice; env vars
# override for per-deployment tuning.
STAPEL_COMM = {
    "ACTION_TRANSPORT": os.getenv("STAPEL_ACTION_TRANSPORT", "inprocess"),
    "FUNCTION_TRANSPORT": os.getenv("STAPEL_FUNCTION_TRANSPORT", "inprocess"),
    # "bus" sends task.* events through the broker (STAPEL_BUS_BACKEND)
    # even when Actions stay in-process — long-running Tasks execute in a
    # dedicated worker instead of the web process.
    "TASK_DISPATCH": os.getenv("STAPEL_TASK_DISPATCH", "action"),
    "NATS_URL": os.getenv("NATS_URL", "nats://nats:4222"),
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_DEFAULT_QUEUE = "app"

# ─── Scheduled workers ─────────────────────────────────────────────────────
# svc-app.yml runs a beat process, so every module that owns a periodic job
# has to be represented here or the job simply never runs — silently. Each
# module publishes its own schedule as a function instead of a snippet to
# copy: the names, the tasks and the crontabs move with the library, and a
# host that merges the function can never hold a stale copy of them.
#
# stapel_billing.W105 makes that mechanical: a host that HAS a beat schedule
# and does not schedule the three billing workers is reported, because an
# unscheduled credit-lot expiry is retention nobody can see. The gdpr half
# carries the export/closure/DSAR clocks (gdpr 0.5 added the data-owner
# probe and the DSAR deadline sweep).
#
# Both modules import cleanly at settings time (celery + stdlib only, no
# models), which is why this can be a merge here rather than a wiring step
# in AppConfig.ready.
from stapel_billing.tasks import get_billing_beat_schedule  # noqa: E402
from stapel_gdpr.tasks import get_gdpr_beat_schedule  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    **get_gdpr_beat_schedule(),
    **get_billing_beat_schedule(),
}

# ─── GDPR — the inventory of stores holding personal data ──────────────────
# gdpr.E001 is an Error, not a warning: with no DATA_OWNERS no account
# closure can reach DELETED and every export is reported to the user as
# partial. The map is owner → the subject types that owner can actually
# erase (gdpr 0.5 widened the value from a bare list of names).
#
# Every registered provider must appear (gdpr.E002 names the ones that do
# not): auth, profile, workspaces, billing, media (cdn), notifications,
# translations. Each row says only what that module's erasure surface, at
# the version pinned in requirements.txt, actually erases — claiming a
# subject an owner cannot erase makes the orchestrator wait for a receipt
# that never comes.
STAPEL_GDPR = {
    "DATA_OWNERS": {
        "auth": ["account"],
        "profile": ["account"],
        # stapel-workspaces 0.29: "This module claims two: account and
        # workspace."
        "workspaces": ["account", "workspace"],
        "billing": ["account"],
        # stapel-cdn 0.14's own declaration of what CDNGDPRProvider erases.
        "media": ["account", "workspace", "file", "recording"],
        "notifications": ["account"],
        "translations": ["account"],
    },
    # Bump whenever DATA_OWNERS changes — a closure records the inventory
    # version that certified it (gdpr.W003).
    "DATA_OWNERS_VERSION": "2026-08-23.1",
}

from stapel_core.django.openapi.swagger import get_spectacular_settings
SPECTACULAR_SETTINGS = get_spectacular_settings(
    title="Stapel Example Monolith API",
    description="Stapel Example Monolith service API",
    # Real version (svc-app/version.txt), not the historical "1.0.0"
    # placeholder — this app isn't an installed pip distribution itself
    # (package= would just fall back), so pass the value already resolved
    # above instead of hardcoding a lie into info.version.
    version=APP_VERSION_NUMBER,
)
