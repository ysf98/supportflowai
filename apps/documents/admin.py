from django.contrib import admin

from .models import Document, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ("index", "token_count", "metadata")
    readonly_fields = fields


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status", "uploaded_by", "created_at")
    list_filter = ("status", "source_type", "content_type")
    search_fields = ("title", "original_filename", "organization__name")
    readonly_fields = (
        "source_type",
        "status",
        "original_filename",
        "content_type",
        "size",
        "extracted_text",
        "error_message",
        "created_at",
        "updated_at",
    )
    inlines = [DocumentChunkInline]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "organization",
        "index",
        "token_count",
        "embedding_status",
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "embedding_generated_at",
        "created_at",
    )
    list_filter = ("organization", "embedding_status", "embedding_provider")
    search_fields = ("document__title", "content")
    readonly_fields = (
        "embedding_status",
        "embedding_provider",
        "embedding_model",
        "embedding_generated_at",
        "embedding_error",
        "embedding_dimension",
    )

    def embedding_dimension(self, obj):
        return len(obj.embedding) if obj.embedding is not None else 0
