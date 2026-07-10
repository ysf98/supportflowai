from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Organization, OrganizationMembership
from .services import build_unique_organization_slug

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "current_user_role", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "current_user_role", "created_at", "updated_at"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_current_user_role(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        if request.user.is_superuser:
            return OrganizationMembership.Role.OWNER
        membership = obj.memberships.filter(user=request.user, is_active=True).first()
        return membership.role if membership else None

    def create(self, validated_data):
        request = self.context["request"]
        name = validated_data["name"]
        organization = Organization.objects.create(
            name=name,
            slug=build_unique_organization_slug(name),
            created_by=request.user,
        )
        OrganizationMembership.objects.create(
            organization=organization,
            user=request.user,
            role=OrganizationMembership.Role.OWNER,
        )
        return organization


class MembershipUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user = MembershipUserSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "role", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class OrganizationMembershipCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "email", "role", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_email(self, value):
        try:
            return User.objects.get(email__iexact=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("No user exists with this email.") from exc

    def validate_role(self, value):
        if value == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError("Use admin actions to transfer ownership.")
        return value

    def create(self, validated_data):
        user = validated_data.pop("email")
        organization = self.context["organization"]
        membership, created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={"role": validated_data["role"], "is_active": True},
        )
        if not created:
            membership.role = validated_data["role"]
            membership.is_active = True
            membership.save(update_fields=["role", "is_active", "updated_at"])
        return membership


class OrganizationMembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = ["role", "is_active"]

    def validate_role(self, value):
        if self.instance and self.instance.role == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError("Owner role cannot be changed here.")
        if value == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError("Use admin actions to transfer ownership.")
        return value
