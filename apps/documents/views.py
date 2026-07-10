from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.serializers import AsyncTaskResponseSerializer
from apps.embeddings.serializers import EmbeddingGenerationSummarySerializer
from apps.embeddings.services import EmbeddingPreconditionError, generate_embeddings_for_document
from apps.embeddings.tasks import generate_document_embeddings_task
from apps.organizations.models import OrganizationMembership
from apps.organizations.permissions import get_user_role, role_at_least

from .models import Document
from .serializers import (
    DocumentChunkSerializer,
    DocumentCreateSerializer,
    DocumentListSerializer,
    DocumentSerializer,
)
from .services.processing import process_document
from .tasks import process_document_task


class DocumentPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        role = get_user_role(request.user, obj.organization)
        if request.method in SAFE_METHODS:
            return role is not None
        return role_at_least(role, OrganizationMembership.Role.ADMIN)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.none()
    permission_classes = [DocumentPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["organization", "status", "source_type"]
    search_fields = ["title", "original_filename"]
    ordering_fields = ["created_at", "updated_at", "title", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()

        user = self.request.user
        queryset = (
            Document.objects.select_related("organization", "uploaded_by")
            .annotate(chunk_count=Count("chunks"))
            .all()
        )
        if not user.is_authenticated:
            return Document.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentCreateSerializer
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentChunkSerializer(document.chunks.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        document = self.get_object()
        role = get_user_role(request.user, document.organization)
        if not role_at_least(role, OrganizationMembership.Role.ADMIN):
            self.permission_denied(request)

        processed_document = process_document(document)
        serializer = DocumentSerializer(processed_document, context={"request": request})
        response_status = (
            status.HTTP_200_OK
            if processed_document.status == Document.Status.PROCESSED
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(serializer.data, status=response_status)

    @extend_schema(request=None, responses={202: AsyncTaskResponseSerializer})
    @action(detail=True, methods=["post"], url_path="process-async")
    def process_async(self, request, pk=None):
        document = self.get_object()
        role = get_user_role(request.user, document.organization)
        if not role_at_least(role, OrganizationMembership.Role.ADMIN):
            self.permission_denied(request)

        result = process_document_task.delay(document.id)
        serializer = AsyncTaskResponseSerializer(
            {
                "task_id": result.id,
                "status": "queued",
                "resource_type": "document",
                "resource_id": document.id,
                "detail": "Document processing has been queued.",
            }
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=None, responses={200: EmbeddingGenerationSummarySerializer})
    @action(detail=True, methods=["post"], url_path="generate-embeddings")
    def generate_embeddings(self, request, pk=None):
        document = self.get_object()
        role = get_user_role(request.user, document.organization)
        if not role_at_least(role, OrganizationMembership.Role.ADMIN):
            self.permission_denied(request)

        try:
            summary = generate_embeddings_for_document(document)
        except EmbeddingPreconditionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = EmbeddingGenerationSummarySerializer(summary.__dict__)
        return Response(serializer.data)

    @extend_schema(request=None, responses={202: AsyncTaskResponseSerializer})
    @action(detail=True, methods=["post"], url_path="generate-embeddings-async")
    def generate_embeddings_async(self, request, pk=None):
        document = self.get_object()
        role = get_user_role(request.user, document.organization)
        if not role_at_least(role, OrganizationMembership.Role.ADMIN):
            self.permission_denied(request)

        if document.status != Document.Status.PROCESSED:
            return Response(
                {"detail": "Document must be processed before generating embeddings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not document.chunks.exists():
            return Response(
                {"detail": "Document has no chunks to embed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = generate_document_embeddings_task.delay(document.id)
        serializer = AsyncTaskResponseSerializer(
            {
                "task_id": result.id,
                "status": "queued",
                "resource_type": "document",
                "resource_id": document.id,
                "detail": "Document embedding generation has been queued.",
            }
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
