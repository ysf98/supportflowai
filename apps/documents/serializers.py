from django.conf import settings
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.organizations.models import Organization
from apps.organizations.permissions import get_user_role, role_at_least
from apps.organizations.models import OrganizationMembership

from .models import Document, DocumentChunk
from .services.extraction import validate_document_file


class DocumentChunkSerializer(serializers.ModelSerializer):
    has_embedding = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "index",
            "content",
            "metadata",
            "token_count",
            "embedding_status",
            "embedding_provider",
            "embedding_model",
            "embedding_generated_at",
            "embedding_error",
            "has_embedding",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_has_embedding(self, obj):
        return obj.embedding is not None


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "organization",
            "organization_name",
            "uploaded_by",
            "title",
            "file",
            "source_type",
            "status",
            "original_filename",
            "content_type",
            "size",
            "extracted_text",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uploaded_by",
            "source_type",
            "status",
            "original_filename",
            "content_type",
            "size",
            "extracted_text",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        ]

    def validate_organization(self, organization):
        request = self.context["request"]
        role = get_user_role(request.user, organization)
        if not role_at_least(role, OrganizationMembership.Role.ADMIN):
            raise serializers.ValidationError("You cannot upload documents to this organization.")
        return organization

    def validate_file(self, uploaded_file):
        validate_document_file(uploaded_file)
        if settings.SUPPORTFLOW_MAX_UPLOAD_SIZE and uploaded_file.size > settings.SUPPORTFLOW_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("Uploaded file is too large.")
        return uploaded_file

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        request = self.context["request"]
        title = validated_data.get("title") or uploaded_file.name
        return Document.objects.create(
            organization=validated_data["organization"],
            uploaded_by=request.user,
            title=title,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", ""),
            size=uploaded_file.size,
        )


class DocumentCreateSerializer(DocumentSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)


class DocumentListSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "organization",
            "organization_name",
            "uploaded_by",
            "title",
            "source_type",
            "status",
            "original_filename",
            "content_type",
            "size",
            "chunk_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
