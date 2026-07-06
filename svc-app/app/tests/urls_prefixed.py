"""The whole monolith mounted under a path prefix (the sub-path deploy shape).

Every URL of the project — every module, the admin, the dev tools — lives
below ``stapel-studio/``. Used by test_mounting.py to prove the login chain
survives a non-empty mount prefix.
"""
from django.urls import include, path

urlpatterns = [
    path("stapel-studio/", include("core.urls")),
]
