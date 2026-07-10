import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationMembership

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_user_and_initial_organization():
    client = APIClient()

    response = client.post(
        reverse("auth-register"),
        {
            "email": "owner@example.com",
            "name": "Owner User",
            "password": "strong-password-123",
            "organization_name": "Acme Support",
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="owner@example.com")
    membership = OrganizationMembership.objects.get(user=user)
    assert membership.organization.name == "Acme Support"
    assert membership.role == OrganizationMembership.Role.OWNER
    assert response.data["organization"]["name"] == "Acme Support"


@pytest.mark.django_db
def test_login_with_email_returns_tokens():
    User.objects.create_user(email="agent@example.com", password="strong-password-123")
    client = APIClient()

    response = client.post(
        reverse("token-obtain-pair"),
        {"email": "agent@example.com", "password": "strong-password-123"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_me_endpoint_returns_authenticated_user():
    user = User.objects.create_user(
        email="me@example.com",
        password="strong-password-123",
        name="Me",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("user-me"))

    assert response.status_code == 200
    assert response.data["email"] == "me@example.com"


@pytest.mark.django_db
def test_me_endpoint_updates_name_only():
    user = User.objects.create_user(
        email="me@example.com",
        password="strong-password-123",
        name="Old",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.patch(
        reverse("user-me"),
        {"name": "New", "email": "changed@example.com"},
        format="json",
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.name == "New"
    assert user.email == "me@example.com"
