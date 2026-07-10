import logging

from celery import shared_task

from .models import Ticket
from .services import classify_ticket, suggest_ticket_reply

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def classify_ticket_task(self, ticket_id: int) -> dict:
    ticket = Ticket.objects.get(pk=ticket_id)
    logger.info("Classifying ticket %s with task %s.", ticket_id, self.request.id)
    classification = classify_ticket(ticket)
    return {
        "ticket_id": ticket.id,
        "category": classification.category,
        "priority": classification.priority,
    }


@shared_task(bind=True)
def suggest_ticket_reply_task(self, ticket_id: int) -> dict:
    ticket = Ticket.objects.get(pk=ticket_id)
    logger.info("Generating suggested reply for ticket %s with task %s.", ticket_id, self.request.id)
    suggested_reply = suggest_ticket_reply(ticket)
    return {
        "ticket_id": ticket.id,
        "suggested_reply_length": len(suggested_reply),
    }
