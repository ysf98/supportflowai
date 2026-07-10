import pytest
from django.contrib.auth import get_user_model

from apps.ai.exceptions import AIProviderError
from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import (
    EmbeddingPreconditionError,
    generate_embedding_for_chunk,
    generate_embeddings_for_document,
    semantic_search,
)
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


class FailingProvider:
    name = "failing"
    embedding_model = "failing-model"
    embedding_dimensions = 16

    def embed_text(self, text):
        raise RuntimeError("provider unavailable with safe message")


def create_processed_document_with_chunks(owner, organization, *, title="Guide"):
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title=title,
        file="documents/test/guide.txt",
        original_filename="guide.txt",
        content_type="text/plain",
        size=100,
        status=Document.Status.PROCESSED,
        extracted_text="Reset password instructions. Billing support instructions.",
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="Reset password instructions for support agents.",
        token_count=6,
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=1,
        content="Billing support instructions for invoices.",
        token_count=5,
    )
    return document


@pytest.mark.django_db
def test_generate_embedding_for_chunk_marks_ready():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document_with_chunks(owner, organization)
    chunk = document.chunks.first()

    generate_embedding_for_chunk(chunk)

    chunk.refresh_from_db()
    assert chunk.embedding_status == DocumentChunk.EmbeddingStatus.READY
    assert chunk.embedding_provider == "fake"
    assert chunk.embedding_model == "fake-embedding-16"
    assert len(chunk.embedding) == 16


@pytest.mark.django_db
def test_generate_embeddings_for_document_marks_all_chunks_ready():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document_with_chunks(owner, organization)

    summary = generate_embeddings_for_document(document)

    assert summary.chunks_processed == 2
    assert summary.chunks_failed == 0
    assert summary.status == "completed"
    assert document.chunks.filter(embedding_status=DocumentChunk.EmbeddingStatus.READY).count() == 2


@pytest.mark.django_db
def test_generate_embeddings_requires_processed_document():
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

    with pytest.raises(EmbeddingPreconditionError):
        generate_embeddings_for_document(document)


@pytest.mark.django_db
def test_generate_embedding_marks_failed_when_provider_fails(monkeypatch):
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document_with_chunks(owner, organization)
    chunk = document.chunks.first()
    monkeypatch.setattr("apps.embeddings.services.get_ai_provider", lambda: FailingProvider())

    with pytest.raises(AIProviderError):
        generate_embedding_for_chunk(chunk)

    chunk.refresh_from_db()
    assert chunk.embedding_status == DocumentChunk.EmbeddingStatus.FAILED
    assert chunk.embedding is None
    assert "provider unavailable" in chunk.embedding_error


@pytest.mark.django_db
def test_semantic_search_returns_results_for_organization_only():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    document_a = create_processed_document_with_chunks(owner_a, organization_a, title="A Guide")
    document_b = create_processed_document_with_chunks(owner_b, organization_b, title="B Guide")
    generate_embeddings_for_document(document_a)
    generate_embeddings_for_document(document_b)

    results = semantic_search(organization_a, "Reset password instructions for support agents.", limit=5)

    assert results
    assert {result.document_id for result in results} == {document_a.id}
    assert results[0].distance <= results[-1].distance


@pytest.mark.django_db
def test_semantic_search_respects_limit():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document_with_chunks(owner, organization)
    generate_embeddings_for_document(document)

    results = semantic_search(organization, "support", limit=1)

    assert len(results) == 1


@pytest.mark.django_db
def test_semantic_search_returns_empty_without_ready_embeddings():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    create_processed_document_with_chunks(owner, organization)

    results = semantic_search(organization, "support", limit=5)

    assert results == []
