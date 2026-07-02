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
# multi-service stack. Leave empty to use Django's own admin login.
AUTH_SERVICE_PREFIX = os.getenv("AUTH_SERVICE_PREFIX", "")

INSTALLED_APPS = COMMON_INSTALLED_APPS + [
    "stapel_auth",
    "stapel_gdpr",
    "stapel_profiles",
    "stapel_notifications",
    "stapel_workspaces",
    "stapel_billing",
    "stapel_cdn",
    "stapel_translate",
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

LOGIN_REDIRECT_URL = "/admin/"
AUTH_USER_MODEL = "users.User"

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
