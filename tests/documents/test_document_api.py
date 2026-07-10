import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.organizations.models import OrganizationMembership
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_owner_can_upload_txt_document(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        file_obj = SimpleUploadedFile(
            "handbook.txt",
            b"Support handbook",
            content_type="text/plain",
        )

        response = authenticate(owner).post(
            reverse("document-list"),
            {"organization": organization.id, "title": "Handbook", "file": file_obj},
            format="multipart",
        )

        assert response.status_code == 201
        document = Document.objects.get()
        assert document.organization == organization
        assert document.uploaded_by == owner
        assert document.status == Document.Status.UPLOADED


@pytest.mark.django_db
def test_viewer_cannot_upload_document(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        viewer = User.objects.create_user(email="viewer@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        OrganizationMembership.objects.create(
            organization=organization,
            user=viewer,
            role=OrganizationMembership.Role.VIEWER,
        )
        file_obj = SimpleUploadedFile(
            "handbook.txt",
            b"Support handbook",
            content_type="text/plain",
        )

        response = authenticate(viewer).post(
            reverse("document-list"),
            {"organization": organization.id, "title": "Handbook", "file": file_obj},
            format="multipart",
        )

        assert response.status_code == 400
        assert Document.objects.count() == 0


@pytest.mark.django_db
def test_unsupported_file_extension_is_rejected(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        file_obj = SimpleUploadedFile(
            "handbook.pdf",
            b"%PDF",
            content_type="application/pdf",
        )

        response = authenticate(owner).post(
            reverse("document-list"),
            {"organization": organization.id, "title": "Handbook", "file": file_obj},
            format="multipart",
        )

        assert response.status_code == 400
        assert Document.objects.count() == 0


@pytest.mark.django_db
def test_process_document_endpoint_creates_chunks(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        uploaded_file = SimpleUploadedFile(
            "guide.txt",
            b" ".join([b"word"] * 260),
            content_type="text/plain",
        )
        document = Document.objects.create(
            organization=organization,
            uploaded_by=owner,
            title="Guide",
            file=uploaded_file,
            original_filename="guide.txt",
            content_type="text/plain",
            size=uploaded_file.size,
        )

        response = authenticate(owner).post(
            reverse("document-process", kwargs={"pk": document.pk})
        )

        document.refresh_from_db()
        assert response.status_code == 200
        assert document.status == Document.Status.PROCESSED
        assert document.chunks.count() == 2


@pytest.mark.django_db
def test_user_cannot_see_other_organization_documents(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner_a = User.objects.create_user(email="a@example.com", password="password-123")
        owner_b = User.objects.create_user(email="b@example.com", password="password-123")
        organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
        create_organization_with_owner(name="Org B", owner=owner_b)
        uploaded_file = SimpleUploadedFile(
            "guide.txt",
            b"Support guide",
            content_type="text/plain",
        )
        Document.objects.create(
            organization=organization_a,
            uploaded_by=owner_a,
            title="Guide",
            file=uploaded_file,
            original_filename="guide.txt",
            content_type="text/plain",
            size=uploaded_file.size,
        )

        response = authenticate(owner_b).get(reverse("document-list"))

        assert response.status_code == 200
        assert response.data["count"] == 0
