import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings

from apps.chat.models import AnswerSource, Conversation, Message
from apps.documents.models import Document, DocumentChunk
from apps.evaluations.models import EvaluationCase, EvaluationRun
from apps.organizations.models import Organization, OrganizationMembership
from apps.tickets.models import Ticket, TicketComment

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_data_creates_complete_demo_dataset(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        call_command("seed_demo_data")

    user = User.objects.get(email="demo@example.com")
    organization = Organization.objects.get(name="Demo Workspace")
    document = Document.objects.get(title="Demo Support Knowledge Base")

    assert user.check_password("DemoPass123!")
    assert OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.OWNER,
    ).exists()
    assert document.organization == organization
    assert document.status == Document.Status.PROCESSED
    assert document.chunks.exists()
    assert DocumentChunk.objects.filter(
        document=document,
        embedding_status=DocumentChunk.EmbeddingStatus.READY,
        embedding__isnull=False,
    ).exists()
    assert Conversation.objects.filter(organization=organization, user=user).exists()
    assert Message.objects.filter(conversation__organization=organization).count() >= 2
    assert AnswerSource.objects.filter(message__conversation__organization=organization).exists()
    assert Ticket.objects.filter(organization=organization).count() == 2
    assert TicketComment.objects.filter(ticket__organization=organization).exists()
    assert Ticket.objects.filter(organization=organization).exclude(ai_summary="").count() == 2
    assert EvaluationCase.objects.filter(organization=organization).exists()
    assert EvaluationRun.objects.filter(organization=organization).exists()


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent_for_main_resources(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        call_command("seed_demo_data")
        call_command("seed_demo_data")

    organization = Organization.objects.get(name="Demo Workspace")

    assert User.objects.filter(email="demo@example.com").count() == 1
    assert Organization.objects.filter(name="Demo Workspace").count() == 1
    assert Document.objects.filter(organization=organization, title="Demo Support Knowledge Base").count() == 1
    assert Conversation.objects.filter(organization=organization, title="Demo: Password reset support").count() == 1
    assert Ticket.objects.filter(organization=organization).count() == 2
    assert EvaluationCase.objects.filter(organization=organization).count() == 1
    assert EvaluationRun.objects.filter(organization=organization).count() == 1
