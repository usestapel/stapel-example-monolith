from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

if not SECRET_KEY or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set in production")
if not JWT_SECRET_KEY or JWT_SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("JWT_SECRET_KEY environment variable must be set in production")
