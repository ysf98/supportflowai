import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationMembership
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_agent_can_create_ticket():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    agent = User.objects.create_user(email="agent@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=agent,
        role=OrganizationMembership.Role.AGENT,
    )

    response = authenticate(agent).post(
        reverse("ticket-list"),
        {
            "organization": organization.id,
            "title": "Login issue",
            "description": "Customer cannot log in.",
        },
        format="json",
    )

    assert response.status_code == 201
    ticket = Ticket.objects.get()
    assert ticket.created_by == agent
    assert ticket.organization == organization


@pytest.mark.django_db
def test_viewer_cannot_create_ticket():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=viewer,
        role=OrganizationMembership.Role.VIEWER,
    )

    response = authenticate(viewer).post(
        reverse("ticket-list"),
        {
            "organization": organization.id,
            "title": "Login issue",
            "description": "Customer cannot log in.",
        },
        format="json",
    )

    assert response.status_code == 400
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_user_only_lists_own_organization_tickets():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    ticket_a = Ticket.objects.create(
        organization=organization_a,
        created_by=owner_a,
        title="A",
        description="A ticket",
    )
    Ticket.objects.create(
        organization=organization_b,
        created_by=owner_b,
        title="B",
        description="B ticket",
    )

    response = authenticate(owner_a).get(reverse("ticket-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == ticket_a.id


@pytest.mark.django_db
def test_user_cannot_access_other_organization_ticket():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    ticket = Ticket.objects.create(
        organization=organization_a,
        created_by=owner_a,
        title="A",
        description="A ticket",
    )

    response = authenticate(owner_b).get(reverse("ticket-detail", kwargs={"pk": ticket.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_agent_can_add_comment():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    agent = User.objects.create_user(email="agent@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=agent,
        role=OrganizationMembership.Role.AGENT,
    )
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Issue",
        description="Needs help.",
    )

    response = authenticate(agent).post(
        reverse("ticket-comments", kwargs={"pk": ticket.pk}),
        {"content": "Investigating.", "is_internal": True},
        format="json",
    )

    assert response.status_code == 201
    assert ticket.comments.get().author == agent


@pytest.mark.django_db
def test_owner_can_classify_ticket():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Urgent billing issue",
        description="Payment failed.",
    )

    response = authenticate(owner).post(reverse("ticket-classify", kwargs={"pk": ticket.pk}))

    assert response.status_code == 200
    assert response.data["category"] == Ticket.Category.BILLING
    ticket.refresh_from_db()
    assert ticket.ai_summary


@pytest.mark.django_db
def test_owner_can_suggest_reply():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Login issue",
        description="Customer cannot access account.",
    )

    response = authenticate(owner).post(reverse("ticket-suggest-reply", kwargs={"pk": ticket.pk}))

    assert response.status_code == 200
    assert "suggested_reply" in response.data
    ticket.refresh_from_db()
    assert ticket.ai_suggested_reply == response.data["suggested_reply"]


@pytest.mark.django_db
def test_agent_can_resolve_ticket_with_comment():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    agent = User.objects.create_user(email="agent@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=agent,
        role=OrganizationMembership.Role.AGENT,
    )
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Issue",
        description="Needs help.",
    )

    response = authenticate(agent).post(
        reverse("ticket-resolve", kwargs={"pk": ticket.pk}),
        {"comment": "Resolved."},
        format="json",
    )

    ticket.refresh_from_db()
    assert response.status_code == 200
    assert ticket.status == Ticket.Status.RESOLVED
    assert ticket.comments.get().content == "Resolved."


@pytest.mark.django_db
def test_viewer_cannot_classify_ticket():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=viewer,
        role=OrganizationMembership.Role.VIEWER,
    )
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Issue",
        description="Needs help.",
    )

    response = authenticate(viewer).post(reverse("ticket-classify", kwargs={"pk": ticket.pk}))

    assert response.status_code == 403
