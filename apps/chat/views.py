from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ai.exceptions import AIProviderError

from .models import Conversation
from .serializers import (
    AskQuestionRequestSerializer,
    AskQuestionResponseSerializer,
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
)
from .services import ChatPermissionError, ask_question


class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.none()
    permission_classes = [IsAuthenticated]
    search_fields = ["title", "organization__name"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()

        user = self.request.user
        queryset = (
            Conversation.objects.select_related("organization", "user")
            .prefetch_related("messages__sources")
            .annotate(message_count=Count("messages"))
        )
        if not user.is_authenticated:
            return Conversation.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return ConversationCreateSerializer
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationListSerializer

    @extend_schema(request=ConversationCreateSerializer, responses={201: ConversationDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        response_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: MessageSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageSerializer(conversation.messages.all(), many=True)
        return Response(serializer.data)

    @extend_schema(
        request=AskQuestionRequestSerializer,
        responses={200: AskQuestionResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def ask(self, request, pk=None):
        conversation = self.get_object()
        serializer = AskQuestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ask_question(
                conversation=conversation,
                user=request.user,
                question=serializer.validated_data["question"],
                limit=serializer.validated_data["limit"],
            )
        except ChatPermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except AIProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        response_serializer = AskQuestionResponseSerializer(
            {
                "conversation_id": result.conversation.id,
                "user_message": result.user_message,
                "assistant_message": result.assistant_message,
                "sources": result.sources,
            }
        )
        return Response(response_serializer.data)
