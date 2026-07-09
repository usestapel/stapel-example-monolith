"""Settings for the all-modules codegen instance (flow-system.md §0.1).

This is the *codegen source*: a live all-modules Django instance whose only job
is to emit the language-agnostic backend artifacts the frontend codegen
consumes — the unified drf-spectacular OpenAPI schema, flows.json, errors.json
and the localized feature bundles.

Hermetic by design: sqlite (in-memory) + local-memory cache, no postgres, no
redis, no broker. The sqlite constraint is architectural: emitting a schema
never touches the database, so postgres is not needed. geo is the documented
exception (needs spatialite) and is not in the monolith module set, so this
instance stays pure-sqlite.

Run:
    DJANGO_ENV=local DJANGO_SETTINGS_MODULE=config.settings.codegen \\
        python -m stapel_tools.codegen --out ../codegen/generated
"""
import os

# get_dev_urls() only mounts /schema/ + /swagger/ when DJANGO_ENV is local/dev.
# The offline `spectacular` management command does not depend on it, but keeping
# the env consistent means the *same* instance also serves an identical /schema/
# for the frontend dev loop.
os.environ.setdefault("DJANGO_ENV", "local")

from .base import *  # noqa: F401,F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "django-insecure-codegen-only"
    JWT_SECRET_KEY = JWT_SECRET_KEY or SECRET_KEY  # noqa: F405

# Hermetic sqlite: schema/flows generation is pure introspection, no DB I/O.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# No redis: schema generation must not require a broker/cache server.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "stapel-codegen",
    }
}
