import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentChunk
from apps.embeddings.services import generate_embeddings_for_document
from apps.evaluations.models import EvaluationCase
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
def test_user_can_create_evaluation_case_in_own_organization():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)

    response = authenticate(owner).post(
        reverse("evaluation-case-list"),
        {
            "organization": organization.id,
            "question": "How do users reset passwords?",
            "expected_answer": "Use account settings.",
        },
        format="json",
    )

    assert response.status_code == 201
    evaluation_case = EvaluationCase.objects.get()
    assert evaluation_case.created_by == owner


@pytest.mark.django_db
def test_user_cannot_create_evaluation_case_in_other_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)

    response = authenticate(owner_b).post(
        reverse("evaluation-case-list"),
        {
            "organization": organization_a.id,
            "question": "How do users reset passwords?",
        },
        format="json",
    )

    assert response.status_code == 400
    assert EvaluationCase.objects.count() == 0


@pytest.mark.django_db
def test_user_only_lists_own_organization_evaluation_cases():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    case_a = EvaluationCase.objects.create(
        organization=organization_a,
        created_by=owner_a,
        question="A?",
    )
    EvaluationCase.objects.create(
        organization=organization_b,
        created_by=owner_b,
        question="B?",
    )

    response = authenticate(owner_a).get(reverse("evaluation-case-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == case_a.id


@pytest.mark.django_db
def test_user_can_run_evaluation_case():
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
        reverse("evaluation-case-run", kwargs={"pk": evaluation_case.pk}),
        {"limit": 5},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["case"] == evaluation_case.id
    assert response.data["retrieved_sources"]


@pytest.mark.django_db
def test_user_cannot_run_other_organization_evaluation_case():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    create_organization_with_owner(name="Org B", owner=owner_b)
    evaluation_case = EvaluationCase.objects.create(
        organization=organization_a,
        created_by=owner_a,
        question="A?",
    )

    response = authenticate(owner_b).post(
        reverse("evaluation-case-run", kwargs={"pk": evaluation_case.pk}),
        {"limit": 5},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_evaluation_runs_are_filtered_by_organization():
    owner_a = User.objects.create_user(email="a@example.com", password="password-123")
    owner_b = User.objects.create_user(email="b@example.com", password="password-123")
    organization_a = create_organization_with_owner(name="Org A", owner=owner_a)
    organization_b = create_organization_with_owner(name="Org B", owner=owner_b)
    case_a = EvaluationCase.objects.create(
        organization=organization_a,
        created_by=owner_a,
        question="A?",
    )
    case_b = EvaluationCase.objects.create(
        organization=organization_b,
        created_by=owner_b,
        question="B?",
    )
    run_a = case_a.runs.create(
        organization=organization_a,
        generated_answer="A",
        retrieved_sources=[],
        score=0.25,
        passed=False,
    )
    case_b.runs.create(
        organization=organization_b,
        generated_answer="B",
        retrieved_sources=[],
        score=0.25,
        passed=False,
    )

    response = authenticate(owner_a).get(reverse("evaluation-run-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == run_a.id
