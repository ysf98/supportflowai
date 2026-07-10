import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentChunk
from apps.documents.tasks import process_document_task
from apps.embeddings.services import generate_embeddings_for_document
from apps.embeddings.tasks import generate_document_embeddings_task
from apps.evaluations.models import EvaluationCase, EvaluationRun
from apps.evaluations.tasks import run_evaluation_case_task
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket
from apps.tickets.tasks import classify_ticket_task, suggest_ticket_reply_task

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
def test_process_document_task_creates_chunks(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Org", owner=owner)
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

        result = process_document_task.delay(document.id)

        document.refresh_from_db()
        assert result.successful()
        assert result.result["status"] == Document.Status.PROCESSED
        assert document.status == Document.Status.PROCESSED
        assert document.chunks.count() == 2


@pytest.mark.django_db
def test_generate_document_embeddings_task_marks_chunks_ready():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)

    result = generate_document_embeddings_task.delay(document.id)

    chunk = document.chunks.get()
    chunk.refresh_from_db()
    assert result.successful()
    assert result.result["chunks_processed"] == 1
    assert chunk.embedding_status == DocumentChunk.EmbeddingStatus.READY


@pytest.mark.django_db
def test_ticket_ai_tasks_update_ticket():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Urgent billing issue",
        description="Payment failed.",
    )

    classification_result = classify_ticket_task.delay(ticket.id)
    reply_result = suggest_ticket_reply_task.delay(ticket.id)

    ticket.refresh_from_db()
    assert classification_result.successful()
    assert reply_result.successful()
    assert ticket.category == Ticket.Category.BILLING
    assert ticket.ai_summary
    assert ticket.ai_suggested_reply


@pytest.mark.django_db
def test_run_evaluation_case_task_creates_run():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    generate_embeddings_for_document(document)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=owner,
        question="How do users reset passwords?",
        expected_answer="reset password account settings",
        expected_document=document,
    )

    result = run_evaluation_case_task.delay(evaluation_case.id, owner.id, 5)

    assert result.successful()
    assert EvaluationRun.objects.filter(case=evaluation_case).count() == 1
    assert result.result["evaluation_run_id"] == EvaluationRun.objects.get().id


@pytest.mark.django_db
def test_document_async_api_queues_processing(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Org", owner=owner)
        uploaded_file = SimpleUploadedFile("guide.txt", b"Support guide", content_type="text/plain")
        document = Document.objects.create(
            organization=organization,
            uploaded_by=owner,
            title="Guide",
            file=uploaded_file,
            original_filename="guide.txt",
            content_type="text/plain",
            size=uploaded_file.size,
        )

        response = authenticate(owner).post(reverse("document-process-async", kwargs={"pk": document.pk}))

        document.refresh_from_db()
        assert response.status_code == 202
        assert response.data["status"] == "queued"
        assert response.data["resource_id"] == document.id
        assert document.status == Document.Status.PROCESSED


@pytest.mark.django_db
def test_embedding_async_api_queues_generation():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)

    response = authenticate(owner).post(
        reverse("document-generate-embeddings-async", kwargs={"pk": document.pk})
    )

    assert response.status_code == 202
    assert response.data["resource_type"] == "document"
    assert document.chunks.get().embedding_status == DocumentChunk.EmbeddingStatus.READY


@pytest.mark.django_db
def test_ticket_async_api_queues_classification():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Urgent billing issue",
        description="Payment failed.",
    )

    response = authenticate(owner).post(reverse("ticket-classify-async", kwargs={"pk": ticket.pk}))

    ticket.refresh_from_db()
    assert response.status_code == 202
    assert response.data["resource_type"] == "ticket"
    assert ticket.category == Ticket.Category.BILLING


@pytest.mark.django_db
def test_evaluation_async_api_queues_run():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    generate_embeddings_for_document(document)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=owner,
        question="How do users reset passwords?",
        expected_answer="reset password account settings",
        expected_document=document,
    )

    response = authenticate(owner).post(
        reverse("evaluation-case-run-async", kwargs={"pk": evaluation_case.pk}),
        {"limit": 5},
        format="json",
    )

    assert response.status_code == 202
    assert response.data["resource_type"] == "evaluation_case"
    assert EvaluationRun.objects.filter(case=evaluation_case).exists()
