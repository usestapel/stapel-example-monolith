"""Test profile — hermetic sqlite, no postgres/redis/debug-toolbar.

The pytest suite runs against this profile (``pytest.ini``). It layers on
``base`` (NOT ``dev``/``local``, which pull in debug_toolbar and its GDAL/postgis
import chain) and swaps the two infra dependencies the tests do not need:

- **sqlite in-memory** instead of postgres — every model in the monolith
  migrates cleanly on sqlite (geo, the one spatialite exception, is not in the
  monolith module set); the admin-suite matrix is pure ``has_perm`` /
  admin-client logic and never depends on the backend.
- **locmem cache** instead of redis — sessions (cache-backed) and the
  verification grant store both live in the cache; a per-process locmem cache
  keeps step-up grants working in-test without a server.

Run:
    DJANGO_SETTINGS_MODULE=core.settings.test \\
        /Users/apple/Projects/stapel/.venv/bin/python -m pytest app/
"""
from .base import *  # noqa: F401,F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "django-insecure-test-only"
    JWT_SECRET_KEY = JWT_SECRET_KEY or SECRET_KEY  # noqa: F405

# Hermetic sqlite: the admin-suite tests exercise permission logic, not SQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# No redis: sessions and the step-up verification grant store are cache-backed;
# a local-memory cache keeps both working in-process.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "stapel-monolith-test",
    }
}
