from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Organization, OrganizationMembership
from .permissions import IsOrganizationAdminOrOwner, OrganizationRolePermission, get_user_role
from .serializers import (
    OrganizationMembershipCreateSerializer,
    OrganizationMembershipSerializer,
    OrganizationMembershipUpdateSerializer,
    OrganizationSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.none()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, OrganizationRolePermission]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()

        user = self.request.user
        queryset = Organization.objects.all().prefetch_related("memberships")
        if not user.is_authenticated:
            return Organization.objects.none()
        if user.is_superuser:
            return queryset
        return queryset.filter(memberships__user=user, memberships__is_active=True).distinct()

    def get_permissions(self):
        if self.action in {"create", "list"}:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        organization = self.get_object()

        if request.method == "GET":
            memberships = organization.memberships.select_related("user").all()
            serializer = OrganizationMembershipSerializer(memberships, many=True)
            return Response(serializer.data)

        permission = IsOrganizationAdminOrOwner()
        if not permission.has_object_permission(request, self, organization):
            self.permission_denied(request)

        serializer = OrganizationMembershipCreateSerializer(
            data=request.data,
            context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(
            OrganizationMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"members/(?P<member_id>\d+)",
    )
    def member_detail(self, request, pk=None, member_id=None):
        organization = self.get_object()

        permission = IsOrganizationAdminOrOwner()
        if not permission.has_object_permission(request, self, organization):
            self.permission_denied(request)

        membership = get_object_or_404(
            organization.memberships.select_related("user"),
            pk=member_id,
        )

        if membership.role == OrganizationMembership.Role.OWNER:
            return Response(
                {"detail": "Owner membership cannot be modified from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "DELETE":
            membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = OrganizationMembershipUpdateSerializer(
            membership,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationMembershipSerializer(membership).data)

    def perform_destroy(self, instance):
        role = get_user_role(self.request.user, instance)
        if role != OrganizationMembership.Role.OWNER:
            self.permission_denied(self.request)
        instance.delete()
