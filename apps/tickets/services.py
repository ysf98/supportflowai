from dataclasses import dataclass

from django.db import transaction

from apps.ai.providers import get_ai_provider

from .models import Ticket, TicketComment


@dataclass(frozen=True)
class TicketClassification:
    category: str
    priority: str
    summary: str


def classify_ticket_content(*, title: str, description: str) -> TicketClassification:
    text = f"{title}\n{description}".lower()

    if any(term in text for term in ["invoice", "billing", "payment", "refund"]):
        category = Ticket.Category.BILLING
    elif any(term in text for term in ["password", "login", "account", "access"]):
        category = Ticket.Category.ACCOUNT
    elif any(term in text for term in ["bug", "error", "api", "server", "technical"]):
        category = Ticket.Category.TECHNICAL
    elif any(term in text for term in ["feature", "product", "plan"]):
        category = Ticket.Category.PRODUCT
    else:
        category = Ticket.Category.OTHER

    if any(term in text for term in ["urgent", "down", "outage", "blocked", "critical"]):
        priority = Ticket.Priority.URGENT
    elif any(term in text for term in ["asap", "high", "broken", "cannot"]):
        priority = Ticket.Priority.HIGH
    elif any(term in text for term in ["question", "minor", "low"]):
        priority = Ticket.Priority.LOW
    else:
        priority = Ticket.Priority.MEDIUM

    summary = f"{title.strip()}: {description.strip()[:180]}"
    return TicketClassification(category=category, priority=priority, summary=summary)


@transaction.atomic
def classify_ticket(ticket: Ticket) -> TicketClassification:
    classification = classify_ticket_content(
        title=ticket.title,
        description=ticket.description,
    )
    ticket.category = classification.category
    ticket.priority = classification.priority
    ticket.ai_summary = classification.summary
    ticket.save(update_fields=["category", "priority", "ai_summary", "updated_at"])
    return classification


def build_ticket_reply_context(ticket: Ticket) -> str:
    comments = ticket.comments.order_by("created_at")
    comment_context = "\n".join(
        f"- {'internal' if comment.is_internal else 'public'}: {comment.content}"
        for comment in comments
    )
    return "\n".join(
        [
            f"Title: {ticket.title}",
            f"Description: {ticket.description}",
            f"Category: {ticket.category}",
            f"Priority: {ticket.priority}",
            "Comments:",
            comment_context or "No comments yet.",
        ]
    )


@transaction.atomic
def suggest_ticket_reply(ticket: Ticket) -> str:
    provider = get_ai_provider()
    context = build_ticket_reply_context(ticket)
    prompt = (
        "Draft a concise, helpful support reply for this ticket. "
        "Do not claim actions were completed unless they are in the context.\n\n"
        f"{context}"
    )
    suggested_reply = provider.generate_text(
        prompt=prompt,
        question=f"Suggest a support reply for: {ticket.title}",
        context=context,
    )
    ticket.ai_suggested_reply = suggested_reply
    ticket.save(update_fields=["ai_suggested_reply", "updated_at"])
    return suggested_reply


@transaction.atomic
def resolve_ticket(*, ticket: Ticket, user, comment: str = "") -> Ticket:
    ticket.status = Ticket.Status.RESOLVED
    ticket.save(update_fields=["status", "updated_at"])
    if comment.strip():
        TicketComment.objects.create(
            ticket=ticket,
            author=user,
            content=comment.strip(),
            is_internal=False,
        )
    return ticket
