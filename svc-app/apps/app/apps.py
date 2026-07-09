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
