from django.conf import settings
from django.urls import reverse


def test_django_settings_load():
    assert settings.ROOT_URLCONF == "config.urls"


def test_api_schema_route_is_registered():
    assert reverse("schema") == "/api/schema/"
