import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.dashboard.services import build_dashboard_summary
from apps.documents.models import Document, DocumentChunk
from apps.evaluations.models import EvaluationCase, EvaluationRun
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket

User = get_user_model()


def authenticate(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_summary_data(owner, organization):
    document = Document.objects.create(
        organization=organization,
        uploaded_by=owner,
        title="FAQ",
        file="documents/test/faq.txt",
        original_filename="faq.txt",
        content_type="text/plain",
        size=100,
        status=Document.Status.PROCESSED,
    )
    DocumentChunk.objects.create(
        organization=organization,
        document=document,
        index=0,
        content="Reset password instructions.",
        token_count=3,
        embedding=[0.1] * 16,
        embedding_status=DocumentChunk.EmbeddingStatus.READY,
        embedding_provider="fake",
        embedding_model="fake-embedding-16",
    )
    conversation = Conversation.objects.create(
        organization=organization,
        user=owner,
        title="Password",
    )
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content="Question?")
    Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content="Answer.")
    Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Urgent issue",
        description="System down.",
        status=Ticket.Status.RESOLVED,
        priority=Ticket.Priority.URGENT,
        ai_summary="Urgent issue summary.",
        ai_suggested_reply="Suggested reply.",
    )
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=owner,
        question="Question?",
    )
    EvaluationRun.objects.create(
        organization=organization,
        case=evaluation_case,
        generated_answer="Answer.",
        retrieved_sources=[],
        score=0.8,
        passed=True,
    )


@pytest.mark.django_db
def test_dashboard_summary_counts_accessible_organization_data_only():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    create_summary_data(owner_a, organization_a)
    create_summary_data(owner_b, organization_b)

    summary = build_dashboard_summary(user=owner_a)

    assert summary.organizations == 1
    assert summary.documents_total == 1
    assert summary.chunks_with_embeddings == 1
    assert summary.conversations_total == 1
    assert summary.questions_total == 1
    assert summary.tickets_resolved == 1
    assert summary.tickets_urgent == 1
    assert summary.evaluations_passed == 1
    assert summary.evaluation_pass_rate == 1.0


@pytest.mark.django_db
def test_superuser_dashboard_summary_counts_all_organizations():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    superuser = User.objects.create_superuser(email="admin@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    create_summary_data(owner_a, organization_a)
    create_summary_data(owner_b, organization_b)

    summary = build_dashboard_summary(user=superuser)

    assert summary.organizations == 2
    assert summary.documents_total == 2
    assert summary.tickets_total == 2


@pytest.mark.django_db
def test_dashboard_summary_endpoint_requires_authentication():
    response = APIClient().get(reverse("dashboard-summary"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_dashboard_summary_endpoint_returns_metrics():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    create_summary_data(owner, organization)

    response = authenticate(owner).get(reverse("dashboard-summary"))

    assert response.status_code == 200
    assert response.data["documents_total"] == 1
    assert response.data["ai_operations_estimated"] >= 1
