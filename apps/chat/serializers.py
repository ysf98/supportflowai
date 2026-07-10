from rest_framework import serializers

from apps.organizations.models import Organization
from apps.organizations.permissions import get_user_role

from .models import AnswerSource, Conversation, Message
from .services import create_conversation


class AnswerSourceSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = AnswerSource
        fields = [
            "id",
            "document",
            "document_title",
            "chunk",
            "distance",
            "score",
            "excerpt",
            "created_at",
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sources = AnswerSourceSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ["id", "role", "content", "sources", "created_at"]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "organization",
            "organization_name",
            "user",
            "title",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization_name", "user", "message_count", "created_at", "updated_at"]


class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ["messages"]


class ConversationCreateSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_organization(self, organization):
        request = self.context["request"]
        if get_user_role(request.user, organization) is None:
            raise serializers.ValidationError("You cannot create a conversation in this organization.")
        return organization

    def create(self, validated_data):
        return create_conversation(
            user=self.context["request"].user,
            organization=validated_data["organization"],
            title=validated_data.get("title"),
        )


class AskQuestionRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class AskQuestionResponseSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    user_message = MessageSerializer()
    assistant_message = MessageSerializer()
    sources = AnswerSourceSerializer(many=True)
