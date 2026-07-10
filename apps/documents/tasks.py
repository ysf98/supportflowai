import logging

from celery import shared_task

from .models import Document
from .services.processing import process_document

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_document_task(self, document_id: int) -> dict:
    document = Document.objects.get(pk=document_id)
    logger.info("Processing document %s with task %s.", document_id, self.request.id)
    processed_document = process_document(document)
    return {
        "document_id": processed_document.id,
        "status": processed_document.status,
        "chunk_count": processed_document.chunks.count(),
    }
