from rest_framework import serializers


class AsyncTaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    resource_type = serializers.CharField()
    resource_id = serializers.IntegerField()
    detail = serializers.CharField()
