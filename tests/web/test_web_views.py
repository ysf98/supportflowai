import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.chat.models import Conversation
from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import generate_embeddings_for_document
from apps.evaluations.models import EvaluationCase
from apps.organizations.models import Organization
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket

User = get_user_model()


@pytest.mark.django_db
def test_dashboard_redirects_anonymous_user(client):
    response = client.get(reverse("web-dashboard"))

    assert response.status_code == 302
    assert reverse("web-login") in response.url


@pytest.mark.django_db
def test_register_creates_user_and_organization(client):
    response = client.post(
        reverse("web-register"),
        {
            "email": "new@example.com",
            "name": "New User",
            "password": "password-123",
            "organization_name": "New Org",
        },
    )

    assert response.status_code == 302
    assert User.objects.filter(email="new@example.com").exists()
    assert Organization.objects.filter(name="New Org").exists()


@pytest.mark.django_db
def test_dashboard_renders_for_authenticated_user(client):
    user = User.objects.create_user(email="owner@example.com", password="password-123")
    create_organization_with_owner(name="Org", owner=user)
    client.force_login(user)

    response = client.get(reverse("web-dashboard"))

    assert response.status_code == 200
    assert b"Dashboard" in response.content


@pytest.mark.django_db
def test_document_upload_page_creates_document(client, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        user = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Org", owner=user)
        client.force_login(user)
        uploaded_file = SimpleUploadedFile("faq.txt", b"Password reset docs", content_type="text/plain")

        response = client.post(
            reverse("web-documents"),
            {
                "organization": organization.id,
                "title": "FAQ",
                "file": uploaded_file,
            },
        )

        assert response.status_code == 302
        assert Document.objects.filter(title="FAQ").exists()


@pytest.mark.django_db
def test_chat_detail_can_ask_question(client):
    user = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=user)
    document = Document.objects.create(
        organization=organization,
        uploaded_by=user,
        title="FAQ",
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=10,
        status=Document.Status.PROCESSED,
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="To reset your password, use account settings.",
        token_count=7,
    )
    generate_embeddings_for_document(document)
    conversation = Conversation.objects.create(organization=organization, user=user, title="FAQ")
    client.force_login(user)

    response = client.post(
        reverse("web-conversation-detail", kwargs={"pk": conversation.pk}),
        {"question": "How do users reset passwords?", "limit": 5},
    )

    assert response.status_code == 302
    assert conversation.messages.count() == 2


@pytest.mark.django_db
def test_ticket_detail_classify_action(client):
    user = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=user)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=user,
        title="Urgent billing issue",
        description="Payment failed.",
    )
    client.force_login(user)

    response = client.post(
        reverse("web-ticket-detail", kwargs={"pk": ticket.pk}),
        {"action": "classify"},
    )

    ticket.refresh_from_db()
    assert response.status_code == 302
    assert ticket.ai_summary


@pytest.mark.django_db
def test_evaluation_detail_run_action(client):
    user = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=user)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=user,
        question="Unknown?",
    )
    client.force_login(user)

    response = client.post(
        reverse("web-evaluation-detail", kwargs={"pk": evaluation_case.pk}),
        {"limit": 5},
    )

    assert response.status_code == 302
    assert evaluation_case.runs.count() == 1
