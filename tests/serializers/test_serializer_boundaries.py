import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.chat.serializers import AskQuestionRequestSerializer, ConversationCreateSerializer
from apps.documents.models import Document
from apps.evaluations.serializers import EvaluationCaseCreateSerializer
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def request_for(user):
    request = APIRequestFactory().post("/")
    request.user = user
    return request


@pytest.mark.django_db
def test_conversation_create_serializer_rejects_foreign_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    serializer = ConversationCreateSerializer(
        data={"organization": organization_a.id, "title": "Foreign"},
        context={"request": request_for(owner_b)},
    )

    assert not serializer.is_valid()
    assert "organization" in serializer.errors


@pytest.mark.django_db
def test_evaluation_case_serializer_rejects_expected_document_from_other_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    foreign_document = Document.objects.create(
        organization=organization_b,
        uploaded_by=owner_b,
        title="Foreign FAQ",
        file="documents/test/foreign.txt",
        original_filename="foreign.txt",
        content_type="text/plain",
        size=10,
    )

    serializer = EvaluationCaseCreateSerializer(
        data={
            "organization": organization_a.id,
            "question": "How does this work?",
            "expected_answer": "Expected answer",
            "expected_document": foreign_document.id,
        },
        context={"request": request_for(owner_a)},
    )

    assert not serializer.is_valid()
    assert "expected_document" in serializer.errors


def test_ask_question_serializer_enforces_limit_bounds():
    too_large = AskQuestionRequestSerializer(
        data={"question": "How can users reset passwords?", "limit": 21}
    )
    too_small = AskQuestionRequestSerializer(
        data={"question": "How can users reset passwords?", "limit": 0}
    )

    assert not too_large.is_valid()
    assert "limit" in too_large.errors
    assert not too_small.is_valid()
    assert "limit" in too_small.errors


def test_ask_question_serializer_requires_non_blank_question():
    serializer = AskQuestionRequestSerializer(data={"question": "   ", "limit": 5})

    assert not serializer.is_valid()
    assert "question" in serializer.errors
