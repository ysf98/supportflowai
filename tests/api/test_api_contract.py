import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.chat.models import Conversation
from apps.documents.models import Document
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_list_endpoints_support_page_size():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    for index in range(3):
        Document.objects.create(
            organization=organization,
            uploaded_by=owner,
            title=f"Doc {index}",
            file=f"documents/test/doc-{index}.txt",
            original_filename=f"doc-{index}.txt",
            content_type="text/plain",
            size=10,
        )

    response = authenticate(owner).get(reverse("document-list"), {"page_size": 2})

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
def test_documents_filter_search_and_ordering():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Password FAQ",
        file="documents/test/password.txt",
        original_filename="password.txt",
        content_type="text/plain",
        size=10,
        status=Document.Status.PROCESSED,
    )
    Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Billing FAQ",
        file="documents/test/billing.txt",
        original_filename="billing.txt",
        content_type="text/plain",
        size=10,
        status=Document.Status.UPLOADED,
    )

    response = authenticate(owner).get(
        reverse("document-list"),
        {"status": Document.Status.PROCESSED, "search": "password", "ordering": "title"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Password FAQ"


@pytest.mark.django_db
def test_tickets_filter_search_and_ordering():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Password problem",
        description="Cannot login",
        priority=Ticket.Priority.URGENT,
    )
    Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Billing question",
        description="Invoice",
        priority=Ticket.Priority.LOW,
    )

    response = authenticate(owner).get(
        reverse("ticket-list"),
        {"priority": Ticket.Priority.URGENT, "search": "password", "ordering": "-created_at"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Password problem"


@pytest.mark.django_db
def test_conversations_search():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    Conversation.objects.create(organization=organization, user=owner, title="Password reset")
    Conversation.objects.create(organization=organization, user=owner, title="Billing")

    response = authenticate(owner).get(reverse("conversation-list"), {"search": "password"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Password reset"


@pytest.mark.django_db
def test_openapi_schema_endpoint_is_available():
    response = APIClient().get(reverse("schema"))

    assert response.status_code == 200
    assert "openapi" in response.data


@pytest.mark.django_db
def test_openapi_schema_documents_core_product_endpoints():
    response = APIClient().get(reverse("schema"))

    assert response.status_code == 200
    paths = response.data["paths"]
    expected_paths = [
        "/api/documents/{id}/process-async/",
        "/api/documents/{id}/generate-embeddings-async/",
        "/api/search/semantic/",
        "/api/conversations/{id}/ask/",
        "/api/tickets/{id}/classify-async/",
        "/api/tickets/{id}/suggest-reply-async/",
        "/api/evaluation-cases/{id}/run-async/",
        "/api/dashboard/summary/",
    ]

    for path in expected_paths:
        assert path in paths
