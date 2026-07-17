from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Full dotted path — the service's own app lives under the apps/ regular
    # package (apps/__init__.py present), same as every stapel-new-module app
    # (Django ticket #24801).
    name = "apps.app"
    # Explicit, collision-proof label: a service named after a hosted Stapel
    # module (e.g. "auth", "profiles") would otherwise take the bare "app"
    # label and clash with django.contrib.auth / stapel_app (which sets
    # label="app"), raising ImproperlyConfigured before any test collects.
    # The "_local" suffix marks this as the SERVICE'S OWN app (vs. the hosted
    # stapel_* module) and mirrors the config.settings.local naming convention.
    label = "app_local"
    verbose_name = "Stapel Example Monolith"

    def ready(self):
        _unpoison_spectacular_settings_cache()


def _unpoison_spectacular_settings_cache():
    """Work around a drf-spectacular / stapel_core import-order bug that
    permanently blanks ``info.title``/``info.version`` in every schema this
    process emits (live ``/schema/``, Swagger UI, and the offline
    ``spectacular`` management command the codegen aggregate is built from).

    Root cause: ``config/settings/base.py`` starts with ``from
    stapel_core.django.settings import *``. Importing that submodule first
    requires fully executing its parent package, ``stapel_core/django/
    __init__.py``, which imports ``stapel_core.django.openapi`` →
    ``stapel_core.django.openapi.schemas`` — the latter does a *non-lazy*
    ``from drf_spectacular.openapi import AutoSchema`` (needed as a base
    class for ``PermissionAwareAutoSchema``, so it can't be deferred the
    way ``stapel_core.django.openapi.swagger`` deliberately defers its own
    drf-spectacular imports). That cascades into importing
    ``drf_spectacular.settings``, whose module body constructs the
    module-level ``spectacular_settings`` *singleton* by snapshotting
    ``django.conf.settings.SPECTACULAR_SETTINGS`` right then — i.e. *before*
    this settings module reaches its own ``SPECTACULAR_SETTINGS =
    get_spectacular_settings(...)`` assignment further down. drf-spectacular
    never re-reads the setting afterwards (no ``setting_changed`` receiver
    for it), so the singleton stays pinned to the empty defaults ('' /
    '0.0.0') for the rest of the process.

    ``AppConfig.ready()`` runs from ``apps.populate()``, which Django calls
    only *after* settings are fully resolved — so patching the
    already-constructed singleton here, in place, via the
    apply_patches/clear_patches seam drf-spectacular ships for exactly this
    kind of override, reaches every module that already did ``from
    drf_spectacular.settings import spectacular_settings`` (same object,
    not a fresh one). ``spectacular_settings.reload()`` would *not* work:
    ``SpectacularSettings`` inherits ``APISettings.user_settings`` as-is,
    which is hardwired to the ``REST_FRAMEWORK`` key, not
    ``SPECTACULAR_SETTINGS``.
    """
    try:
        from drf_spectacular.settings import spectacular_settings
    except ImportError:
        return

    from django.conf import settings as django_settings

    real = getattr(django_settings, "SPECTACULAR_SETTINGS", None) or {}
    patches = {
        key: real[key]
        for key in ("TITLE", "VERSION", "DESCRIPTION")
        if real.get(key) and getattr(spectacular_settings, key, None) != real[key]
    }
    if patches:
        spectacular_settings.apply_patches(patches)
