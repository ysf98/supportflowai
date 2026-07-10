import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import generate_embeddings_for_document
from apps.organizations.models import OrganizationMembership
from apps.organizations.services import create_organization_with_owner

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
        extracted_text="Password reset. Billing support.",
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="To reset your password, use account settings.",
        token_count=8,
    )
    return document


@pytest.mark.django_db
def test_unauthenticated_user_cannot_search():
    response = APIClient().post(
        reverse("semantic-search"),
        {"organization": 1, "query": "password", "limit": 5},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_member_can_search_own_organization():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    generate_embeddings_for_document(document)

    response = authenticate(owner).post(
        reverse("semantic-search"),
        {"organization": organization.id, "query": "reset password", "limit": 5},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["query"] == "reset password"
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["document_id"] == document.id


@pytest.mark.django_db
def test_user_cannot_search_other_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    response = authenticate(owner_b).post(
        reverse("semantic-search"),
        {"organization": organization_a.id, "query": "password", "limit": 5},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_owner_can_generate_document_embeddings():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)

    response = authenticate(owner).post(
        reverse("document-generate-embeddings", kwargs={"pk": document.pk})
    )

    assert response.status_code == 200
    assert response.data["chunks_processed"] == 1
    assert response.data["chunks_failed"] == 0
    assert document.chunks.get().embedding_status == DocumentChunk.EmbeddingStatus.READY


@pytest.mark.django_db
def test_viewer_cannot_generate_document_embeddings():
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
        reverse("document-generate-embeddings", kwargs={"pk": document.pk})
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_cannot_generate_embeddings_for_unprocessed_document():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Draft",
        file="documents/test/draft.txt",
        original_filename="draft.txt",
        content_type="text/plain",
        size=10,
        status=Document.Status.UPLOADED,
    )

    response = authenticate(owner).post(
        reverse("document-generate-embeddings", kwargs={"pk": document.pk})
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_user_cannot_generate_embeddings_for_other_organization_document():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    document = create_processed_document(owner_a, organization_a)

    response = authenticate(owner_b).post(
        reverse("document-generate-embeddings", kwargs={"pk": document.pk})
    )

    assert response.status_code == 404
