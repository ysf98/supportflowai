from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.serializers import AsyncTaskResponseSerializer

from .models import EvaluationCase, EvaluationRun
from .serializers import (
    EvaluationCaseCreateSerializer,
    EvaluationCaseSerializer,
    EvaluationRunSerializer,
    RunEvaluationRequestSerializer,
    RunEvaluationResponseSerializer,
)
from .services import run_evaluation_case
from .tasks import run_evaluation_case_task


class EvaluationCaseViewSet(viewsets.ModelViewSet):
    queryset = EvaluationCase.objects.none()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["organization", "expected_document"]
    search_fields = ["question", "expected_answer"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return EvaluationCase.objects.none()

        user = self.request.user
        queryset = EvaluationCase.objects.select_related(
            "organization",
            "created_by",
            "expected_document",
        ).prefetch_related("runs")
        if not user.is_authenticated:
            return EvaluationCase.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return EvaluationCaseCreateSerializer
        return EvaluationCaseSerializer

    @extend_schema(
        request=RunEvaluationRequestSerializer,
        responses={200: RunEvaluationResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        evaluation_case = self.get_object()
        serializer = RunEvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation_run = run_evaluation_case(
            evaluation_case=evaluation_case,
            user=request.user,
            limit=serializer.validated_data["limit"],
        )
        return Response(EvaluationRunSerializer(evaluation_run).data)

    @extend_schema(
        request=RunEvaluationRequestSerializer,
        responses={202: AsyncTaskResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="run-async")
    def run_async(self, request, pk=None):
        evaluation_case = self.get_object()
        serializer = RunEvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = run_evaluation_case_task.delay(
            evaluation_case.id,
            request.user.id,
            serializer.validated_data["limit"],
        )
        response_serializer = AsyncTaskResponseSerializer(
            {
                "task_id": result.id,
                "status": "queued",
                "resource_type": "evaluation_case",
                "resource_id": evaluation_case.id,
                "detail": "Evaluation run has been queued.",
            }
        )
        return Response(response_serializer.data, status=202)


class EvaluationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EvaluationRun.objects.none()
    serializer_class = EvaluationRunSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["organization", "case", "passed"]
    ordering_fields = ["created_at", "score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return EvaluationRun.objects.none()

        user = self.request.user
        queryset = EvaluationRun.objects.select_related("organization", "case")
        if not user.is_authenticated:
            return EvaluationRun.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()
