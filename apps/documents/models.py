from pathlib import Path
import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from apps.core.models import OrganizationScopedModel


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"documents/{instance.organization_id}/{uuid.uuid4().hex}{extension}"


class Document(OrganizationScopedModel):
    class SourceType(models.TextChoices):
        UPLOAD = "upload", "Upload"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.UPLOAD,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    extracted_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def extension(self):
        return Path(self.original_filename).suffix.lower()


class DocumentChunk(OrganizationScopedModel):
    class EmbeddingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    index = models.PositiveIntegerField()
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(
        dimensions=settings.SUPPORTFLOW_EMBEDDING_DIMENSIONS,
        null=True,
        blank=True,
    )
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_provider = models.CharField(max_length=50, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
    )
    embedding_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "index"],
                name="unique_chunk_index_per_document",
            )
        ]
        ordering = ["document_id", "index"]

    def __str__(self):
        return f"{self.document} chunk {self.index}"
