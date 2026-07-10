from dataclasses import dataclass

from apps.chat.models import Conversation, Message
from apps.documents.models import Document, DocumentChunk
from apps.evaluations.models import EvaluationRun
from apps.organizations.models import Organization
from apps.tickets.models import Ticket


@dataclass(frozen=True)
class DashboardSummary:
    organizations: int
    documents_total: int
    documents_processed: int
    documents_failed: int
    chunks_total: int
    chunks_with_embeddings: int
    conversations_total: int
    questions_total: int
    assistant_messages_total: int
    tickets_total: int
    tickets_open: int
    tickets_resolved: int
    tickets_urgent: int
    evaluations_total: int
    evaluations_passed: int
    evaluation_pass_rate: float
    ai_operations_estimated: int
    estimated_ai_cost: float


def get_accessible_organization_ids(user) -> list[int]:
    if user.is_superuser:
        return list(Organization.objects.values_list("id", flat=True))
    return list(
        Organization.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
        )
        .distinct()
        .values_list("id", flat=True)
    )


def build_dashboard_summary(*, user) -> DashboardSummary:
    organization_ids = get_accessible_organization_ids(user)

    documents = Document.objects.filter(organization_id__in=organization_ids)
    chunks = DocumentChunk.objects.filter(organization_id__in=organization_ids)
    conversations = Conversation.objects.filter(organization_id__in=organization_ids)
    messages = Message.objects.filter(conversation__organization_id__in=organization_ids)
    tickets = Ticket.objects.filter(organization_id__in=organization_ids)
    evaluation_runs = EvaluationRun.objects.filter(organization_id__in=organization_ids)

    evaluations_total = evaluation_runs.count()
    evaluations_passed = evaluation_runs.filter(passed=True).count()
    evaluation_pass_rate = (
        round(evaluations_passed / evaluations_total, 3)
        if evaluations_total
        else 0.0
    )

    chunks_with_embeddings = chunks.filter(
        embedding_status=DocumentChunk.EmbeddingStatus.READY,
        embedding__isnull=False,
    ).count()
    assistant_messages_total = messages.filter(role=Message.Role.ASSISTANT).count()
    ai_ticket_operations = tickets.exclude(ai_summary="").count() + tickets.exclude(
        ai_suggested_reply=""
    ).count()

    return DashboardSummary(
        organizations=len(organization_ids),
        documents_total=documents.count(),
        documents_processed=documents.filter(status=Document.Status.PROCESSED).count(),
        documents_failed=documents.filter(status=Document.Status.FAILED).count(),
        chunks_total=chunks.count(),
        chunks_with_embeddings=chunks_with_embeddings,
        conversations_total=conversations.count(),
        questions_total=messages.filter(role=Message.Role.USER).count(),
        assistant_messages_total=assistant_messages_total,
        tickets_total=tickets.count(),
        tickets_open=tickets.filter(status=Ticket.Status.OPEN).count(),
        tickets_resolved=tickets.filter(status=Ticket.Status.RESOLVED).count(),
        tickets_urgent=tickets.filter(priority=Ticket.Priority.URGENT).count(),
        evaluations_total=evaluations_total,
        evaluations_passed=evaluations_passed,
        evaluation_pass_rate=evaluation_pass_rate,
        ai_operations_estimated=chunks_with_embeddings
        + assistant_messages_total
        + ai_ticket_operations
        + evaluations_total,
        estimated_ai_cost=0.0,
    )
