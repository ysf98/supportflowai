from dataclasses import dataclass

from django.db import transaction

from apps.chat.services import ask_question, create_conversation
from apps.organizations.permissions import get_user_role

from .models import EvaluationCase, EvaluationRun


class EvaluationPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class EvaluationScore:
    score: float
    passed: bool
    notes: str


def ensure_evaluation_access(*, user, organization) -> None:
    if get_user_role(user, organization) is None:
        raise EvaluationPermissionError("You cannot access evaluations for this organization.")


def _tokenize(text: str) -> set[str]:
    return {word.strip(".,:;!?()[]{}\"'").lower() for word in text.split() if word.strip()}


def score_evaluation_case(
    *,
    evaluation_case: EvaluationCase,
    generated_answer: str,
    retrieved_sources: list[dict],
) -> EvaluationScore:
    score = 0.0
    notes = []

    if generated_answer.strip():
        score += 0.25
        notes.append("Generated answer is not empty.")
    else:
        notes.append("Generated answer is empty.")

    if retrieved_sources:
        score += 0.25
        notes.append("At least one source was retrieved.")
    else:
        notes.append("No sources were retrieved.")

    if evaluation_case.expected_document_id:
        expected_document_found = any(
            source["document_id"] == evaluation_case.expected_document_id
            for source in retrieved_sources
        )
        if expected_document_found:
            score += 0.25
            notes.append("Expected document was retrieved.")
        else:
            notes.append("Expected document was not retrieved.")
    else:
        score += 0.25
        notes.append("No expected document configured.")

    expected_tokens = _tokenize(evaluation_case.expected_answer)
    if expected_tokens:
        generated_tokens = _tokenize(generated_answer)
        overlap = len(expected_tokens & generated_tokens) / len(expected_tokens)
        score += 0.25 * overlap
        notes.append(f"Expected answer token overlap: {overlap:.2f}.")
    else:
        score += 0.25
        notes.append("No expected answer configured.")

    rounded_score = round(score, 3)
    has_sources = bool(retrieved_sources)
    return EvaluationScore(
        score=rounded_score,
        passed=has_sources and rounded_score >= 0.7,
        notes=" ".join(notes),
    )


def serialize_sources(answer_sources) -> list[dict]:
    return [
        {
            "document_id": source.document_id,
            "document_title": source.document.title,
            "chunk_id": source.chunk_id,
            "score": source.score,
            "distance": source.distance,
            "excerpt": source.excerpt,
        }
        for source in answer_sources
    ]


@transaction.atomic
def run_evaluation_case(*, evaluation_case: EvaluationCase, user, limit: int = 5) -> EvaluationRun:
    ensure_evaluation_access(user=user, organization=evaluation_case.organization)
    conversation = create_conversation(
        user=user,
        organization=evaluation_case.organization,
        title=f"Evaluation: {evaluation_case.question[:80]}",
    )

    result = ask_question(
        conversation=conversation,
        user=user,
        question=evaluation_case.question,
        limit=limit,
    )
    retrieved_sources = serialize_sources(result.sources)
    score = score_evaluation_case(
        evaluation_case=evaluation_case,
        generated_answer=result.assistant_message.content,
        retrieved_sources=retrieved_sources,
    )

    return EvaluationRun.objects.create(
        organization=evaluation_case.organization,
        case=evaluation_case,
        generated_answer=result.assistant_message.content,
        retrieved_sources=retrieved_sources,
        score=score.score,
        passed=score.passed,
        notes=score.notes,
    )
