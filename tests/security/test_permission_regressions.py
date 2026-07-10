import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentChunk
from apps.evaluations.models import EvaluationCase
from apps.organizations.models import OrganizationMembership
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_processed_document(owner, organization):
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Support FAQ",
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=100,
        status=Document.Status.PROCESSED,
        extracted_text="Reset password instructions.",
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="Reset password instructions.",
        token_count=3,
    )
    return document


@pytest.mark.django_db
def test_viewer_cannot_queue_document_processing():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=viewer,
        role=OrganizationMembership.Role.VIEWER,
    )
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Draft",
        file="documents/test/draft.txt",
        original_filename="draft.txt",
        content_type="text/plain",
        size=10,
    )

    response = authenticate(viewer).post(
        reverse("document-process-async", kwargs={"pk": document.pk})
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_viewer_cannot_queue_embedding_generation():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=organization,
        user=viewer,
        role=OrganizationMembership.Role.VIEWER,
    )
    document = create_processed_document(owner, organization)

    response = authenticate(viewer).post(
        reverse("document-generate-embeddings-async", kwargs={"pk": document.pk})
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_viewer_cannot_queue_ticket_ai_actions():
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
        title="Urgent billing issue",
        description="Payment failed.",
    )

    classify_response = authenticate(viewer).post(
        reverse("ticket-classify-async", kwargs={"pk": ticket.pk})
    )
    suggest_response = authenticate(viewer).post(
        reverse("ticket-suggest-reply-async", kwargs={"pk": ticket.pk})
    )

    assert classify_response.status_code == 403
    assert suggest_response.status_code == 403


@pytest.mark.django_db
def test_web_document_detail_hides_foreign_document():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    document = Document.objects.create(
        organization=organization_a,
        uploaded_by=owner_a,
        title="Private FAQ",
        file="documents/test/private.txt",
        original_filename="private.txt",
        content_type="text/plain",
        size=10,
    )
    client = Client()
    client.force_login(owner_b)

    response = client.get(reverse("web-document-detail", kwargs={"pk": document.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_web_evaluation_detail_hides_foreign_case():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization_a,
        created_by=owner_a,
        question="Private?",
    )
    client = Client()
    client.force_login(owner_b)

    response = client.get(reverse("web-evaluation-detail", kwargs={"pk": evaluation_case.pk}))

    assert response.status_code == 404
