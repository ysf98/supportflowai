import pytest
from django.contrib.auth import get_user_model

from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket, TicketComment
from apps.tickets.services import classify_ticket, resolve_ticket, suggest_ticket_reply

User = get_user_model()


@pytest.mark.django_db
def test_classify_ticket_updates_category_priority_and_summary():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Urgent billing problem",
        description="Payment failed and customer is blocked.",
    )

    classification = classify_ticket(ticket)

    ticket.refresh_from_db()
    assert classification.category == Ticket.Category.BILLING
    assert ticket.category == Ticket.Category.BILLING
    assert ticket.priority == Ticket.Priority.URGENT
    assert ticket.ai_summary


@pytest.mark.django_db
def test_suggest_ticket_reply_saves_fake_response():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Login issue",
        description="Customer cannot access the account.",
    )

    suggested_reply = suggest_ticket_reply(ticket)

    ticket.refresh_from_db()
    assert "Fake answer based on the available documents" in suggested_reply
    assert ticket.ai_suggested_reply == suggested_reply


@pytest.mark.django_db
def test_resolve_ticket_sets_status_and_adds_optional_comment():
    owner = User.objects.create_user(email="owner@example.com", password="password-123")
    organization = create_organization_with_owner(name="Org", owner=owner)
    ticket = Ticket.objects.create(
        organization=organization,
        created_by=owner,
        title="Issue",
        description="Needs resolution.",
    )

    resolve_ticket(ticket=ticket, user=owner, comment="Resolved for customer.")

    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.RESOLVED
    assert TicketComment.objects.get(ticket=ticket).content == "Resolved for customer."
