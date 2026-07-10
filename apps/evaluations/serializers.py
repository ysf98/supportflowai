from rest_framework import serializers

from apps.documents.models import Document
from apps.organizations.models import Organization
from apps.organizations.permissions import get_user_role

from .models import EvaluationCase, EvaluationRun
from .services import run_evaluation_case


class EvaluationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationRun
        fields = [
            "id",
            "organization",
            "case",
            "generated_answer",
            "retrieved_sources",
            "score",
            "passed",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EvaluationCaseSerializer(serializers.ModelSerializer):
    runs = EvaluationRunSerializer(many=True, read_only=True)

    class Meta:
        model = EvaluationCase
        fields = [
            "id",
            "organization",
            "question",
            "expected_answer",
            "expected_document",
            "created_by",
            "runs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "runs", "created_at", "updated_at"]

    def validate_organization(self, organization):
        request = self.context["request"]
        if get_user_role(request.user, organization) is None:
            raise serializers.ValidationError("You cannot create evaluations in this organization.")
        return organization

    def validate_expected_document(self, expected_document):
        organization_id = self.initial_data.get("organization")
        if self.instance:
            organization_id = self.instance.organization_id
        if expected_document and organization_id and expected_document.organization_id != int(organization_id):
            raise serializers.ValidationError("Expected document must belong to the evaluation organization.")
        return expected_document

    def create(self, validated_data):
        return EvaluationCase.objects.create(
            created_by=self.context["request"].user,
            **validated_data,
        )


class EvaluationCaseCreateSerializer(EvaluationCaseSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    expected_document = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.all(),
        required=False,
        allow_null=True,
    )


class RunEvaluationRequestSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class RunEvaluationResponseSerializer(EvaluationRunSerializer):
    pass
