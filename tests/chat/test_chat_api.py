import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.chat.models import Conversation
from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import generate_embeddings_for_document
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_processed_document(owner, organization):
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="Support FAQ",
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=100,
        status=Document.Status.PROCESSED,
        extracted_text="To reset your password, use account settings.",
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="To reset your password, use account settings.",
        token_count=7,
    )
    return document


@pytest.mark.django_db
def test_unauthenticated_user_cannot_list_conversations():
    response = APIClient().get(reverse("conversation-list"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_user_can_create_conversation_in_own_organization():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)

    response = authenticate(owner).post(
        reverse("conversation-list"),
        {"organization": organization.id, "title": "Password reset"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["organization"] == organization.id
    assert response.data["title"] == "Password reset"


@pytest.mark.django_db
def test_user_cannot_create_conversation_in_other_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    response = authenticate(owner_b).post(
        reverse("conversation-list"),
        {"organization": organization_a.id, "title": "Nope"},
        format="json",
    )

    assert response.status_code == 400
    assert Conversation.objects.count() == 0


@pytest.mark.django_db
def test_user_only_lists_allowed_conversations():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    conversation_a = Conversation.objects.create(organization=organization_a, user=owner_a, title="A")
    Conversation.objects.create(organization=organization_b, user=owner_b, title="B")

    response = authenticate(owner_a).get(reverse("conversation-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == conversation_a.id


@pytest.mark.django_db
def test_user_cannot_view_other_organization_conversation():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    conversation_a = Conversation.objects.create(organization=organization_a, user=owner_a, title="A")

    response = authenticate(owner_b).get(
        reverse("conversation-detail", kwargs={"pk": conversation_a.pk})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_user_can_ask_in_allowed_conversation():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    generate_embeddings_for_document(document)
    conversation = Conversation.objects.create(organization=organization, user=owner, title="Password")

    response = authenticate(owner).post(
        reverse("conversation-ask", kwargs={"pk": conversation.pk}),
        {"question": "How can users reset their password?", "limit": 5},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["conversation_id"] == conversation.id
    assert response.data["user_message"]["role"] == "user"
    assert response.data["assistant_message"]["role"] == "assistant"
    assert len(response.data["sources"]) == 1
    assert response.data["sources"][0]["document"] == document.id


@pytest.mark.django_db
def test_user_cannot_ask_in_other_organization_conversation():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    conversation = Conversation.objects.create(organization=organization_a, user=owner_a)

    response = authenticate(owner_b).post(
        reverse("conversation-ask", kwargs={"pk": conversation.pk}),
        {"question": "Question?", "limit": 5},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_messages_endpoint_returns_messages_ordered():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    conversation = Conversation.objects.create(organization=organization, user=owner)
    conversation.messages.create(role="user", content="First")
    conversation.messages.create(role="assistant", content="Second")

    response = authenticate(owner).get(
        reverse("conversation-messages", kwargs={"pk": conversation.pk})
    )

    assert response.status_code == 200
    assert [message["content"] for message in response.data] == ["First", "Second"]
