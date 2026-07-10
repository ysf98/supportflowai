import pytest
from django.contrib.auth import get_user_model

from apps.chat.models import AnswerSource, Conversation, Message
from apps.chat.services import (
    ChatPermissionError,
    INSUFFICIENT_CONTEXT_MESSAGE,
    ask_question,
    create_conversation,
    save_answer_sources,
)
from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import SemanticSearchResult, generate_embeddings_for_document
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def create_processed_document(owner, organization, *, title="FAQ", content="To reset your password, use account settings."):
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title=title,
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=100,
        status=Document.Status.PROCESSED,
        extracted_text=content,
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content=content,
        token_count=len(content.split()),
    )
    return document


@pytest.mark.django_db
def test_create_conversation_requires_membership():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    outsider = User.objects.create_user(email="outsider@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)

    with pytest.raises(ChatPermissionError):
        create_conversation(user=outsider, organization=organization)


@pytest.mark.django_db
def test_ask_question_with_context_saves_messages_and_sources():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    generate_embeddings_for_document(document)
    conversation = create_conversation(user=owner, organization=organization, title="Password")

    result = ask_question(
        conversation=conversation,
        user=owner,
        question="How can users reset their password?",
    )

    assert result.user_message.role == Message.Role.USER
    assert result.assistant_message.role == Message.Role.ASSISTANT
    assert "Fake answer based on the available documents" in result.assistant_message.content
    assert len(result.sources) == 1
    assert result.sources[0].document == document


@pytest.mark.django_db
def test_ask_question_without_context_saves_safe_answer_without_sources():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    conversation = create_conversation(user=owner, organization=organization)

    result = ask_question(
        conversation=conversation,
        user=owner,
        question="How can users reset their password?",
    )

    assert result.assistant_message.content == INSUFFICIENT_CONTEXT_MESSAGE
    assert result.sources == []
    assert AnswerSource.objects.count() == 0


@pytest.mark.django_db
def test_ask_question_rejects_non_member():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    outsider = User.objects.create_user(email="outsider@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    conversation = create_conversation(user=owner, organization=organization)

    with pytest.raises(ChatPermissionError):
        ask_question(conversation=conversation, user=outsider, question="Question?")


@pytest.mark.django_db
def test_answer_sources_reject_cross_organization_results():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    document_b = create_processed_document(owner_b, organization_b, title="Other")
    chunk_b = document_b.chunks.get()
    conversation = create_conversation(user=owner_a, organization=organization_a)
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="Answer",
    )

    sources = save_answer_sources(
        message=message,
        search_results=[
            SemanticSearchResult(
                document_organization_id=organization_b.id,
                document_id=document_b.id,
                document_title=document_b.title,
                chunk_organization_id=organization_b.id,
                chunk_id=chunk_b.id,
                chunk_index=chunk_b.index,
                excerpt=chunk_b.content,
                distance=0.1,
                score=0.9,
            )
        ],
    )

    assert sources == []
    assert AnswerSource.objects.count() == 0
