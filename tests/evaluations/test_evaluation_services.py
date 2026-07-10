import pytest
from django.contrib.auth import get_user_model

from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import generate_embeddings_for_document
from apps.evaluations.models import EvaluationCase
from apps.evaluations.services import run_evaluation_case, score_evaluation_case
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


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
def test_score_evaluation_case_passes_with_answer_and_expected_source():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    document = create_processed_document(owner, organization)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=owner,
        question="How do users reset passwords?",
        expected_answer="reset password account settings",
        expected_document=document,
    )

    result = score_evaluation_case(
        evaluation_case=evaluation_case,
        generated_answer="Users reset password from account settings.",
        retrieved_sources=[{"document_id": document.id}],
    )

    assert result.passed is True
    assert result.score >= 0.7


@pytest.mark.django_db
def test_run_evaluation_case_creates_run_with_sources():
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

    evaluation_run = run_evaluation_case(evaluation_case=evaluation_case, user=owner)

    assert evaluation_run.case == evaluation_case
    assert evaluation_run.generated_answer
    assert evaluation_run.retrieved_sources
    assert evaluation_run.retrieved_sources[0]["document_id"] == document.id
    assert evaluation_run.passed is True


@pytest.mark.django_db
def test_run_evaluation_case_handles_no_sources():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization,
        created_by=owner,
        question="Unknown question?",
        expected_answer="not available",
    )

    evaluation_run = run_evaluation_case(evaluation_case=evaluation_case, user=owner)

    assert evaluation_run.retrieved_sources == []
    assert evaluation_run.passed is False
    assert "No sources were retrieved" in evaluation_run.notes
