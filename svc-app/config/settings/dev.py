from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS += ["dev.app.local"]

# File mailtrap for local/dev + async-consumer tests (see tests/harness):
# outbound mail is written to var/mailtrap/ as JSON instead of hitting SMTP.
MAILTRAP_DIR = BASE_DIR / "var" / "mailtrap"
EMAIL_BACKEND = "tests.harness.mailtrap.FileMailtrapBackend"

if not SECRET_KEY:
    SECRET_KEY = "django-insecure-app-dev-only"
    JWT_SECRET_KEY = JWT_SECRET_KEY or SECRET_KEY

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = MIDDLEWARE + ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1", "localhost"]


def show_toolbar(request):
    return request.method == "GET"


DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    "INTERCEPT_REDIRECTS": False,
}

import os
if os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN"):
    try:
        import debugpy
        debugpy.listen(("0.0.0.0", 5678))
        print("debugpy listening on 5678")
    except Exception:
        pass
