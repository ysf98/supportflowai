from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import get_user_role, role_at_least

from .models import Ticket, TicketComment

User = get_user_model()


class TicketCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = TicketComment
        fields = ["id", "author", "author_email", "content", "is_internal", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "author_email", "created_at", "updated_at"]


class TicketSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    assigned_to_email = serializers.EmailField(source="assigned_to.email", read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "organization",
            "organization_name",
            "created_by",
            "created_by_email",
            "assigned_to",
            "assigned_to_email",
            "title",
            "description",
            "status",
            "priority",
            "category",
            "ai_summary",
            "ai_suggested_reply",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_name",
            "created_by",
            "created_by_email",
            "assigned_to_email",
            "ai_summary",
            "ai_suggested_reply",
            "comments",
            "created_at",
            "updated_at",
        ]

    def validate_organization(self, organization):
        request = self.context["request"]
        role = get_user_role(request.user, organization)
        if not role_at_least(role, OrganizationMembership.Role.AGENT):
            raise serializers.ValidationError("You cannot manage tickets in this organization.")
        return organization

    def validate_assigned_to(self, assigned_to):
        organization = self.initial_data.get("organization")
        if self.instance:
            organization = self.instance.organization_id
        if assigned_to and organization:
            if not OrganizationMembership.objects.filter(
                organization_id=organization,
                user=assigned_to,
                is_active=True,
            ).exists():
                raise serializers.ValidationError("Assigned user must belong to the organization.")
        return assigned_to

    def create(self, validated_data):
        return Ticket.objects.create(created_by=self.context["request"].user, **validated_data)


class TicketListSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    assigned_to_email = serializers.EmailField(source="assigned_to.email", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "organization",
            "organization_name",
            "created_by",
            "created_by_email",
            "assigned_to",
            "assigned_to_email",
            "title",
            "status",
            "priority",
            "category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TicketCreateSerializer(TicketSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )


class TicketCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketComment
        fields = ["content", "is_internal"]


class TicketClassificationResponseSerializer(serializers.Serializer):
    category = serializers.CharField()
    priority = serializers.CharField()
    summary = serializers.CharField()


class TicketSuggestedReplyResponseSerializer(serializers.Serializer):
    suggested_reply = serializers.CharField()


class TicketResolveRequestSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)
