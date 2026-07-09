import os

from .base import *  # noqa
from stapel_core.django.prodguard import guard_db_password, guard_secret

DEBUG = False

# Cookies: HttpOnly/SameSite already come from stapel_core.django.settings;
# base/dev leave Secure off so plain-HTTP local dev still works — force it
# here (security-programme.md gap B3).
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
JWT_COOKIE_SECURE = True

# ─── Transport hardening (security-programme.md SEC-4 / gap B1) ───────────
# SECURE_PROXY_SSL_HEADER (set in the common library settings) already trusts
# X-Forwarded-Proto from nginx; override via env only if TLS terminates
# somewhere else entirely.
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"

# HSTS ramp: start conservative — 1 day, no subdomains, no preload — and
# raise SECURE_HSTS_SECONDS to 31536000 (1 year) once HTTPS has been verified
# stable for every host this cookie covers. include_subdomains and preload
# are both one-way doors for the whole domain (preload especially — near
# impossible to reverse once a domain ships in browser preload lists), so
# neither is enabled by default; raising them is a deliberate decision for
# the deploying team, not a default we should force.
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "86400"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True

# Content-Security-Policy — report-only by default (Django's native CSP
# middleware, Django>=6; older Django simply skips the header). A strict
# enforced policy can break django-admin's and Vite's inline scripts/styles
# without per-project tuning, so this ships observing violations rather than
# blocking them. Switch to enforce (rename SECURE_CSP_REPORT_ONLY below to
# SECURE_CSP) once the real source list for this project's frontend is
# known — open question, security-programme.md §8.4.
try:
    from django.utils.csp import CSP

    MIDDLEWARE = MIDDLEWARE + ["django.middleware.csp.ContentSecurityPolicyMiddleware"]
    SECURE_CSP_REPORT_ONLY = {
        "default-src": [CSP.SELF],
        "script-src": [CSP.SELF],
        "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
        "img-src": [CSP.SELF, "data:"],
        "font-src": [CSP.SELF],
    }
except ImportError:
    pass

# ─── Prod-guard (security-programme.md gap B2/B6) ──────────────────────────
# Refuses to boot on a placeholder/too-short secret or the shipped default DB
# password — stapel-create-project (SEC-6) writes real generated values into
# .env at project creation, so this only fires on a copy-pasted .env.example.
guard_secret("SECRET_KEY", SECRET_KEY)
guard_secret("JWT_SECRET_KEY", JWT_SECRET_KEY)
guard_db_password(DATABASES["default"].get("PASSWORD"))
