from django.db import transaction
from django.utils.text import slugify

from .models import Organization, OrganizationMembership


def build_unique_organization_slug(name: str) -> str:
    base_slug = slugify(name) or "organization"
    slug = base_slug
    index = 1

    while Organization.objects.filter(slug=slug).exists():
        index += 1
        slug = f"{base_slug}-{index}"

    return slug


@transaction.atomic
def create_organization_with_owner(*, name: str, owner):
    organization = Organization.objects.create(
        name=name,
        slug=build_unique_organization_slug(name),
        created_by=owner,
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=owner,
        role=OrganizationMembership.Role.OWNER,
    )
    return organization


def user_membership_for_organization(*, user, organization):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return None
    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()
