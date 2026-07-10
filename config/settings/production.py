"""Production settings for SupportFlow AI."""

from .base import *  # noqa: F403

DEBUG = False

if SECRET_KEY == "unsafe-development-key":  # noqa: F405
    raise RuntimeError("SECRET_KEY must be set in production.")

if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("ALLOWED_HOSTS must be set in production.")

if "*" in ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("Wildcard ALLOWED_HOSTS is not allowed in production.")

if DEBUG:  # noqa: F405
    raise RuntimeError("DEBUG must be disabled in production.")

if not CSRF_TRUSTED_ORIGINS:  # noqa: F405
    raise RuntimeError("CSRF_TRUSTED_ORIGINS must be set in production.")

CORS_ALLOW_ALL_ORIGINS = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
