from rest_framework import serializers

from apps.organizations.models import Organization
from apps.organizations.permissions import get_user_role


class EmbeddingGenerationSummarySerializer(serializers.Serializer):
    chunks_processed = serializers.IntegerField()
    chunks_failed = serializers.IntegerField()
    status = serializers.CharField()


class SemanticSearchRequestSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    query = serializers.CharField(max_length=1000)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)

    def validate_organization(self, organization):
        request = self.context["request"]
        if get_user_role(request.user, organization) is None:
            raise serializers.ValidationError("You cannot search this organization.")
        return organization


class SemanticSearchResultSerializer(serializers.Serializer):
    document_organization_id = serializers.IntegerField(write_only=True, required=False)
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    chunk_organization_id = serializers.IntegerField(write_only=True, required=False)
    chunk_id = serializers.IntegerField()
    chunk_index = serializers.IntegerField()
    excerpt = serializers.CharField()
    distance = serializers.FloatField()
    score = serializers.FloatField()


class SemanticSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = SemanticSearchResultSerializer(many=True)
