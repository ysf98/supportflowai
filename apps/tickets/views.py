from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from apps.core.serializers import AsyncTaskResponseSerializer
from apps.organizations.models import OrganizationMembership
from apps.organizations.permissions import get_user_role, role_at_least

from .models import Ticket
from .serializers import (
    TicketClassificationResponseSerializer,
    TicketCommentCreateSerializer,
    TicketCommentSerializer,
    TicketCreateSerializer,
    TicketListSerializer,
    TicketResolveRequestSerializer,
    TicketSerializer,
    TicketSuggestedReplyResponseSerializer,
)
from .services import classify_ticket, resolve_ticket, suggest_ticket_reply
from .tasks import classify_ticket_task, suggest_ticket_reply_task


class TicketPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        role = get_user_role(request.user, obj.organization)
        if request.method in SAFE_METHODS:
            return role is not None
        return role_at_least(role, OrganizationMembership.Role.AGENT)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.none()
    permission_classes = [TicketPermission]
    filterset_fields = ["organization", "status", "priority", "category", "assigned_to"]
    search_fields = ["title", "description", "ai_summary"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()

        user = self.request.user
        queryset = Ticket.objects.select_related("organization", "created_by", "assigned_to").prefetch_related(
            "comments"
        )
        if not user.is_authenticated:
            return Ticket.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer

    @extend_schema(request=TicketCommentCreateSerializer, responses={201: TicketCommentSerializer})
    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        role = get_user_role(request.user, ticket.organization)
        if not role_at_least(role, OrganizationMembership.Role.AGENT):
            self.permission_denied(request)

        serializer = TicketCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = ticket.comments.create(author=request.user, **serializer.validated_data)
        return Response(TicketCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: TicketClassificationResponseSerializer})
    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        ticket = self.get_object()
        classification = classify_ticket(ticket)
        serializer = TicketClassificationResponseSerializer(classification.__dict__)
        return Response(serializer.data)

    @extend_schema(request=None, responses={202: AsyncTaskResponseSerializer})
    @action(detail=True, methods=["post"], url_path="classify-async")
    def classify_async(self, request, pk=None):
        ticket = self.get_object()
        result = classify_ticket_task.delay(ticket.id)
        serializer = AsyncTaskResponseSerializer(
            {
                "task_id": result.id,
                "status": "queued",
                "resource_type": "ticket",
                "resource_id": ticket.id,
                "detail": "Ticket classification has been queued.",
            }
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=None, responses={200: TicketSuggestedReplyResponseSerializer})
    @action(detail=True, methods=["post"], url_path="suggest-reply")
    def suggest_reply(self, request, pk=None):
        ticket = self.get_object()
        suggested_reply = suggest_ticket_reply(ticket)
        serializer = TicketSuggestedReplyResponseSerializer({"suggested_reply": suggested_reply})
        return Response(serializer.data)

    @extend_schema(request=None, responses={202: AsyncTaskResponseSerializer})
    @action(detail=True, methods=["post"], url_path="suggest-reply-async")
    def suggest_reply_async(self, request, pk=None):
        ticket = self.get_object()
        result = suggest_ticket_reply_task.delay(ticket.id)
        serializer = AsyncTaskResponseSerializer(
            {
                "task_id": result.id,
                "status": "queued",
                "resource_type": "ticket",
                "resource_id": ticket.id,
                "detail": "Ticket reply suggestion has been queued.",
            }
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=TicketResolveRequestSerializer, responses={200: TicketSerializer})
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketResolveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resolved = resolve_ticket(
            ticket=ticket,
            user=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(TicketSerializer(resolved, context={"request": request}).data)
