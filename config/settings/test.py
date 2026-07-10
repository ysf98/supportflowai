"""Test settings for SupportFlow AI."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key-for-supportflow-ai-jwt-signing"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

AI_PROVIDER = "fake"
SUPPORTFLOW_EMBEDDING_DIMENSIONS = 16
FAKE_EMBEDDING_DIMENSIONS = 16

DATABASES["default"]["TEST"] = {"NAME": "test_supportflow"}  # noqa: F405
