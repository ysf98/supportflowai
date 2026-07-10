from django.db import transaction

from apps.documents.models import Document, DocumentChunk

from .chunking import split_text_into_chunks
from .extraction import extract_text_from_file


@transaction.atomic
def process_document(document: Document) -> Document:
    document.status = Document.Status.PROCESSING
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])

    try:
        extracted_text = extract_text_from_file(document.file, document.original_filename)
        chunks = split_text_into_chunks(extracted_text)

        document.chunks.all().delete()
        for chunk in chunks:
            DocumentChunk.objects.create(
                organization=document.organization,
                document=document,
                index=chunk.index,
                content=chunk.content,
                metadata=chunk.metadata,
                token_count=chunk.token_count,
            )

        document.extracted_text = extracted_text
        document.status = Document.Status.PROCESSED
        document.error_message = ""
        document.save(
            update_fields=["extracted_text", "status", "error_message", "updated_at"]
        )
    except Exception as exc:
        document.status = Document.Status.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message", "updated_at"])

    return document
