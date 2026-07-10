from dataclasses import dataclass

from django.utils import timezone
from pgvector.django import L2Distance

from apps.ai.exceptions import AIProviderError
from apps.ai.providers import get_ai_provider
from apps.documents.models import Document, DocumentChunk


class EmbeddingPreconditionError(ValueError):
    pass


@dataclass(frozen=True)
class EmbeddingGenerationSummary:
    chunks_processed: int
    chunks_failed: int
    status: str


@dataclass(frozen=True)
class SemanticSearchResult:
    document_organization_id: int
    document_id: int
    document_title: str
    chunk_organization_id: int
    chunk_id: int
    chunk_index: int
    excerpt: str
    distance: float
    score: float


def _safe_error_message(exc: Exception) -> str:
    return str(exc).splitlines()[0][:500]


def generate_embedding_for_chunk(chunk: DocumentChunk) -> DocumentChunk:
    provider = get_ai_provider()
    chunk.embedding_status = DocumentChunk.EmbeddingStatus.PROCESSING
    chunk.embedding_error = ""
    chunk.save(update_fields=["embedding_status", "embedding_error", "updated_at"])

    try:
        embedding = provider.embed_text(chunk.content)
    except Exception as exc:
        chunk.embedding = None
        chunk.embedding_status = DocumentChunk.EmbeddingStatus.FAILED
        chunk.embedding_error = _safe_error_message(exc)
        chunk.save(
            update_fields=[
                "embedding",
                "embedding_status",
                "embedding_error",
                "updated_at",
            ]
        )
        raise AIProviderError(chunk.embedding_error) from exc

    chunk.embedding = embedding
    chunk.embedding_model = provider.embedding_model
    chunk.embedding_provider = provider.name
    chunk.embedding_generated_at = timezone.now()
    chunk.embedding_status = DocumentChunk.EmbeddingStatus.READY
    chunk.embedding_error = ""
    chunk.save(
        update_fields=[
            "embedding",
            "embedding_model",
            "embedding_provider",
            "embedding_generated_at",
            "embedding_status",
            "embedding_error",
            "updated_at",
        ]
    )
    return chunk


def generate_embeddings_for_document(document: Document) -> EmbeddingGenerationSummary:
    if document.status != Document.Status.PROCESSED:
        raise EmbeddingPreconditionError("Document must be processed before generating embeddings.")

    chunks = list(document.chunks.order_by("index"))
    if not chunks:
        raise EmbeddingPreconditionError("Document has no chunks to embed.")

    processed = 0
    failed = 0
    for chunk in chunks:
        try:
            generate_embedding_for_chunk(chunk)
            processed += 1
        except AIProviderError:
            failed += 1

    return EmbeddingGenerationSummary(
        chunks_processed=processed,
        chunks_failed=failed,
        status="completed" if failed == 0 else "completed_with_errors",
    )


def generate_pending_embeddings_for_organization(organization) -> EmbeddingGenerationSummary:
    chunks = DocumentChunk.objects.filter(
        organization=organization,
        embedding_status=DocumentChunk.EmbeddingStatus.PENDING,
        document__status=Document.Status.PROCESSED,
    ).order_by("document_id", "index")

    processed = 0
    failed = 0
    for chunk in chunks:
        try:
            generate_embedding_for_chunk(chunk)
            processed += 1
        except AIProviderError:
            failed += 1

    return EmbeddingGenerationSummary(
        chunks_processed=processed,
        chunks_failed=failed,
        status="completed" if failed == 0 else "completed_with_errors",
    )


def semantic_search(organization, query: str, limit: int = 5) -> list[SemanticSearchResult]:
    if not query.strip():
        return []

    limit = max(1, min(limit, 20))
    provider = get_ai_provider()
    query_embedding = provider.embed_text(query)

    chunks = (
        DocumentChunk.objects.filter(
            organization=organization,
            embedding_status=DocumentChunk.EmbeddingStatus.READY,
            embedding__isnull=False,
        )
        .select_related("document")
        .annotate(distance=L2Distance("embedding", query_embedding))
        .order_by("distance")[:limit]
    )

    results = []
    for chunk in chunks:
        distance = float(chunk.distance)
        results.append(
            SemanticSearchResult(
                document_organization_id=chunk.document.organization_id,
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                chunk_organization_id=chunk.organization_id,
                chunk_id=chunk.id,
                chunk_index=chunk.index,
                excerpt=chunk.content[:500],
                distance=distance,
                score=1 / (1 + distance),
            )
        )
    return results
