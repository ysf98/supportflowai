"""Base settings for SupportFlow AI."""

from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-development-key")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.organizations",
    "apps.documents",
    "apps.embeddings",
    "apps.chat",
    "apps.tickets",
    "apps.ai",
    "apps.evaluations",
    "apps.dashboard",
    "apps.web",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
AUTH_USER_MODEL = "users.User"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://supportflow:supportflow@localhost:5432/supportflow",
)

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
SUPPORTFLOW_MAX_UPLOAD_SIZE = int(os.getenv("SUPPORTFLOW_MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = SUPPORTFLOW_MAX_UPLOAD_SIZE + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = min(SUPPORTFLOW_MAX_UPLOAD_SIZE, 2 * 1024 * 1024)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "web-login"
LOGIN_REDIRECT_URL = "web-dashboard"
LOGOUT_REDIRECT_URL = "web-login"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SupportFlow AI API",
    "DESCRIPTION": "Internal support platform with RAG, tickets, and AI workflows.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "DocumentStatusEnum": "apps.documents.models.Document.Status",
        "TicketStatusEnum": "apps.tickets.models.Ticket.Status",
    },
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "supportflow@example.com")

AI_PROVIDER = os.getenv("AI_PROVIDER", "fake")
SUPPORTFLOW_EMBEDDING_DIMENSIONS = int(os.getenv("SUPPORTFLOW_EMBEDDING_DIMENSIONS", "16"))
FAKE_EMBEDDING_DIMENSIONS = int(os.getenv("FAKE_EMBEDDING_DIMENSIONS", str(SUPPORTFLOW_EMBEDDING_DIMENSIONS)))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "apps.ai": {"handlers": ["console"], "level": os.getenv("SUPPORTFLOW_LOG_LEVEL", "INFO"), "propagate": False},
        "apps.documents": {"handlers": ["console"], "level": os.getenv("SUPPORTFLOW_LOG_LEVEL", "INFO"), "propagate": False},
        "apps.embeddings": {"handlers": ["console"], "level": os.getenv("SUPPORTFLOW_LOG_LEVEL", "INFO"), "propagate": False},
        "apps.tickets": {"handlers": ["console"], "level": os.getenv("SUPPORTFLOW_LOG_LEVEL", "INFO"), "propagate": False},
        "apps.evaluations": {"handlers": ["console"], "level": os.getenv("SUPPORTFLOW_LOG_LEVEL", "INFO"), "propagate": False},
    },
}
