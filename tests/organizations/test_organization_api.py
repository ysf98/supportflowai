import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_user_only_sees_own_organizations():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    org_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    response = authenticate(owner_a).get(reverse("organization-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == org_a.id


@pytest.mark.django_db
def test_owner_can_create_organization():
    user = User.objects.create_user(email="owner@example.com", password="password-123")

    response = authenticate(user).post(
        reverse("organization-list"),
        {"name": "New Org"},
        format="json",
    )

    assert response.status_code == 201
    organization = Organization.objects.get(name="New Org")
    membership = OrganizationMembership.objects.get(organization=organization, user=user)
    assert membership.role == OrganizationMembership.Role.OWNER


@pytest.mark.django_db
def test_viewer_cannot_update_organization():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=viewer,
        role=OrganizationMembership.Role.VIEWER,
    )

    response = authenticate(viewer).patch(
        reverse("organization-detail", kwargs={"pk": organization.pk}),
        {"name": "Renamed"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_add_member():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    admin = User.objects.create_user(email="admin@example.com", password="password-123")
    new_user = User.objects.create_user(email="new@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=admin,
        role=OrganizationMembership.Role.ADMIN,
    )

    response = authenticate(admin).post(
        reverse("organization-members", kwargs={"pk": organization.pk}),
        {"email": "new@example.com", "role": OrganizationMembership.Role.AGENT},
        format="json",
    )

    assert response.status_code == 201
    membership = OrganizationMembership.objects.get(organization=organization, user=new_user)
    assert membership.role == OrganizationMembership.Role.AGENT


@pytest.mark.django_db
def test_agent_cannot_add_member():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    agent = User.objects.create_user(email="agent@example.com", password="password-123")
    new_user = User.objects.create_user(email="new@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=agent,
        role=OrganizationMembership.Role.AGENT,
    )

    response = authenticate(agent).post(
        reverse("organization-members", kwargs={"pk": organization.pk}),
        {"email": new_user.email, "role": OrganizationMembership.Role.VIEWER},
        format="json",
    )

    assert response.status_code == 403
    assert not OrganizationMembership.objects.filter(organization=organization, user=new_user).exists()


@pytest.mark.django_db
def test_member_from_other_organization_cannot_access_detail():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    response = authenticate(owner_b).get(
        reverse("organization-detail", kwargs={"pk": organization_a.pk})
    )

    assert response.status_code == 404
