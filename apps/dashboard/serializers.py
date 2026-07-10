from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    organizations = serializers.IntegerField()
    documents_total = serializers.IntegerField()
    documents_processed = serializers.IntegerField()
    documents_failed = serializers.IntegerField()
    chunks_total = serializers.IntegerField()
    chunks_with_embeddings = serializers.IntegerField()
    conversations_total = serializers.IntegerField()
    questions_total = serializers.IntegerField()
    assistant_messages_total = serializers.IntegerField()
    tickets_total = serializers.IntegerField()
    tickets_open = serializers.IntegerField()
    tickets_resolved = serializers.IntegerField()
    tickets_urgent = serializers.IntegerField()
    evaluations_total = serializers.IntegerField()
    evaluations_passed = serializers.IntegerField()
    evaluation_pass_rate = serializers.FloatField()
    ai_operations_estimated = serializers.IntegerField()
    estimated_ai_cost = serializers.FloatField()
