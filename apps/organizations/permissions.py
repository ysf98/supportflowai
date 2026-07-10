from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Organization, OrganizationMembership


ROLE_ORDER = {
    OrganizationMembership.Role.VIEWER: 10,
    OrganizationMembership.Role.AGENT: 20,
    OrganizationMembership.Role.ADMIN: 30,
    OrganizationMembership.Role.OWNER: 40,
}


def get_user_role(user, organization):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return OrganizationMembership.Role.OWNER
    membership = OrganizationMembership.objects.filter(
        user=user,
        organization=organization,
        is_active=True,
    ).first()
    return membership.role if membership else None


def role_at_least(role, minimum_role):
    if role is None:
        return False
    return ROLE_ORDER[role] >= ROLE_ORDER[minimum_role]


class IsOrganizationMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = obj if isinstance(obj, Organization) else obj.organization
        return get_user_role(request.user, organization) is not None


class IsOrganizationAdminOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = obj if isinstance(obj, Organization) else obj.organization
        role = get_user_role(request.user, organization)
        return role_at_least(role, OrganizationMembership.Role.ADMIN)


class OrganizationRolePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = obj if isinstance(obj, Organization) else obj.organization
        role = get_user_role(request.user, organization)

        if request.method in SAFE_METHODS:
            return role is not None

        if getattr(view, "action", None) == "destroy":
            return role == OrganizationMembership.Role.OWNER

        return role_at_least(role, OrganizationMembership.Role.ADMIN)
