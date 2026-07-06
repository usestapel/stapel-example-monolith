"""URL configuration for the Stapel example monolith.

One Django service hosting every Stapel feature module. Each module is
mounted on its natural prefix (the same paths it would occupy as a separate
microservice), so module-internal links, admin login redirects and frontend
fetches work unchanged.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from stapel_core.django.api.routers import OptionalSlashRouter
from stapel_core.django import get_health_urls
from stapel_core.django.openapi.swagger import get_dev_urls
from stapel_core.django.openapi.mcp import build_mcp_schema_view

url_prefix = settings.URL_PREFIX
service_name = settings.SERVICE_NAME

admin.site.site_header = f"{service_name} Admin"
admin.site.site_title = f"{service_name} Admin"
admin.site.index_title = f"{service_name} Admin — v{settings.APP_VERSION_NUMBER}"

router = OptionalSlashRouter()

mcp_schema_view = build_mcp_schema_view(
    title="Stapel Example Monolith API",
    description="All Stapel modules in one service",
    version="1.0.0",
)

urlpatterns = [
    *get_health_urls(url_prefix),

    # Feature modules on their natural prefixes
    path("auth/api/", include("stapel_auth.urls")),
    path("auth/api/", include("stapel_gdpr.urls")),
    path("profiles/api/", include("stapel_profiles.urls")),
    path("notifications/api/", include("stapel_notifications.urls")),
    path("workspaces/api/", include("stapel_workspaces.urls")),
    path("billing/api/", include("stapel_billing.urls")),
    path("cdn/api/", include("stapel_cdn.urls")),
    path("categories/api/", include("stapel_categories.urls")),
    # stapel_translate.urls carries its own "translate/..." prefix
    path("", include("stapel_translate.urls")),

    # Project-local API and admin
    path(f"{url_prefix}api/", include(router.urls)),
    path("admin/", admin.site.urls),
    *get_dev_urls(url_prefix, mcp_schema_view),
]
