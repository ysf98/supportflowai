from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, inline_serializer

from apps.organizations.models import OrganizationMembership
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "is_active", "date_joined"]
        read_only_fields = ["id", "email", "is_active", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    organization_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    organization = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "password", "organization_name", "organization"]
        read_only_fields = ["id", "organization"]

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    @transaction.atomic
    def create(self, validated_data):
        organization_name = validated_data.pop("organization_name", "")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)

        default_org_name = organization_name.strip() or f"{user.name or user.email}'s Workspace"
        organization = create_organization_with_owner(name=default_org_name, owner=user)
        user.initial_organization = organization
        return user

    @extend_schema_field(
        inline_serializer(
            name="InitialOrganization",
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
                "slug": serializers.CharField(),
            },
        )
    )
    def get_organization(self, obj):
        organization = getattr(obj, "initial_organization", None)
        if organization is None:
            membership = (
                OrganizationMembership.objects.filter(user=obj, role=OrganizationMembership.Role.OWNER)
                .select_related("organization")
                .first()
            )
            organization = membership.organization if membership else None
        if organization is None:
            return None
        return {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
        }
