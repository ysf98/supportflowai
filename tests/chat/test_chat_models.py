import pytest
from django.contrib.auth import get_user_model

from apps.chat.models import AnswerSource, Conversation, Message
from apps.documents.models import Document, DocumentChunk
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


@pytest.mark.django_db
def test_create_conversation_message_and_source():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    conversation = Conversation.objects.create(
        organization=organization,
        user=owner,
        title="Password questions",
    )
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="Use account settings.",
    )
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="FAQ",
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=10,
        status=Document.Status.PROCESSED,
    )
    chunk = DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="Password reset instructions.",
        token_count=3,
    )
    source = AnswerSource.objects.create(
        message=message,
        document=document,
        chunk=chunk,
        distance=0.1,
        score=0.9,
        excerpt=chunk.content,
    )

    assert "Password questions" in str(conversation)
    assert str(message) == f"assistant message in {conversation.id}"
    assert str(source) == f"Source {chunk.id} for message {message.id}"


@pytest.mark.django_db
def test_messages_are_ordered_by_creation():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    conversation = Conversation.objects.create(organization=organization, user=owner)
    first = Message.objects.create(conversation=conversation, role=Message.Role.USER, content="First")
    second = Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content="Second")

    assert list(conversation.messages.all()) == [first, second]
