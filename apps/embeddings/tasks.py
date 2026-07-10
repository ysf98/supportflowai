import logging

from celery import shared_task

from apps.documents.models import Document

from .services import generate_embeddings_for_document, generate_pending_embeddings_for_organization

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_document_embeddings_task(self, document_id: int) -> dict:
    document = Document.objects.get(pk=document_id)
    logger.info("Generating embeddings for document %s with task %s.", document_id, self.request.id)
    summary = generate_embeddings_for_document(document)
    return {
        "document_id": document.id,
        "chunks_processed": summary.chunks_processed,
        "chunks_failed": summary.chunks_failed,
        "status": summary.status,
    }


@shared_task(bind=True)
def generate_organization_pending_embeddings_task(self, organization_id: int) -> dict:
    from apps.organizations.models import Organization

    organization = Organization.objects.get(pk=organization_id)
    logger.info(
        "Generating pending embeddings for organization %s with task %s.",
        organization_id,
        self.request.id,
    )
    summary = generate_pending_embeddings_for_organization(organization)
    return {
        "organization_id": organization.id,
        "chunks_processed": summary.chunks_processed,
        "chunks_failed": summary.chunks_failed,
        "status": summary.status,
    }
