from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.test import override_settings

from apps.chat.models import Conversation
from apps.chat.services import ask_question, create_conversation
from apps.documents.models import Document
from apps.documents.services.processing import process_document
from apps.embeddings.services import generate_embeddings_for_document
from apps.evaluations.models import EvaluationCase, EvaluationRun
from apps.evaluations.services import run_evaluation_case
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket, TicketComment
from apps.tickets.services import classify_ticket, suggest_ticket_reply

User = get_user_model()


DEMO_DOCUMENT = """# SupportFlow Demo Knowledge Base

## Password resets

Users can reset their password from Account Settings by selecting Security, choosing Reset Password, and confirming the email verification code.

If a user cannot access their email, an agent should verify the account owner and escalate the request to the account team.

## Billing support

Billing questions should include the invoice number, account email, and payment provider reference when available.

Refund requests should be reviewed by the billing team before promising a customer-facing resolution.

## Outages

Urgent outage reports should be marked as urgent, assigned to the technical support queue, and summarized for the incident channel.
"""


class Command(BaseCommand):
    help = "Create deterministic demo data for local SupportFlow AI demos."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@example.com")
        parser.add_argument("--password", default="DemoPass123!")
        parser.add_argument("--name", default="Demo User")
        parser.add_argument("--organization", default="Demo Workspace")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        name = options["name"]
        organization_name = options["organization"]

        user = self._get_or_create_user(email=email, password=password, name=name)
        organization = self._get_or_create_organization(user=user, name=organization_name)

        with override_settings(AI_PROVIDER="fake"):
            document = self._get_or_create_document(user=user, organization=organization)
            self._ensure_document_ready(document)
            conversation = self._get_or_create_conversation(user=user, organization=organization)
            self._ensure_conversation_answer(conversation=conversation, user=user)
            tickets = self._get_or_create_tickets(user=user, organization=organization)
            self._ensure_ticket_ai(tickets)
            evaluation_case = self._get_or_create_evaluation_case(
                user=user,
                organization=organization,
                document=document,
            )
            self._ensure_evaluation_run(evaluation_case=evaluation_case, user=user)

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write(f"Organization: {organization.name}")

    def _get_or_create_user(self, *, email: str, password: str, name: str):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"name": name},
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        else:
            updates = []
            if user.name != name:
                user.name = name
                updates.append("name")
            if not user.has_usable_password():
                user.set_password(password)
                updates.append("password")
            if updates:
                user.save(update_fields=updates)
        return user

    def _get_or_create_organization(self, *, user, name: str):
        membership = (
            OrganizationMembership.objects.filter(
                user=user,
                role=OrganizationMembership.Role.OWNER,
                organization__name=name,
            )
            .select_related("organization")
            .first()
        )
        if membership:
            return membership.organization

        organization = Organization.objects.filter(name=name, created_by=user).first()
        if organization is None:
            organization = create_organization_with_owner(name=name, owner=user)
        else:
            OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": OrganizationMembership.Role.OWNER, "is_active": True},
            )
        return organization

    def _get_or_create_document(self, *, user, organization):
        document = Document.objects.filter(
            organization=organization,
            title="Demo Support Knowledge Base",
        ).first()
        if document:
            return document

        document = Document(
            organization=organization,
            uploaded_by=user,
            title="Demo Support Knowledge Base",
            original_filename="supportflow-demo-knowledge.md",
            content_type="text/markdown",
            size=len(DEMO_DOCUMENT.encode("utf-8")),
        )
        document.file.save(
            "supportflow-demo-knowledge.md",
            ContentFile(DEMO_DOCUMENT.encode("utf-8")),
            save=True,
        )
        return document

    def _ensure_document_ready(self, document):
        if document.status != Document.Status.PROCESSED or not document.chunks.exists():
            document = process_document(document)

        has_ready_embeddings = document.chunks.filter(
            embedding_status=document.chunks.model.EmbeddingStatus.READY,
            embedding__isnull=False,
        ).exists()
        if document.status == Document.Status.PROCESSED and not has_ready_embeddings:
            generate_embeddings_for_document(document)

    def _get_or_create_conversation(self, *, user, organization):
        conversation = Conversation.objects.filter(
            organization=organization,
            user=user,
            title="Demo: Password reset support",
        ).first()
        if conversation:
            return conversation
        return create_conversation(
            user=user,
            organization=organization,
            title="Demo: Password reset support",
        )

    def _ensure_conversation_answer(self, *, conversation, user):
        if conversation.messages.exists():
            return
        ask_question(
            conversation=conversation,
            user=user,
            question="How can a user reset their password?",
            limit=5,
        )

    def _get_or_create_tickets(self, *, user, organization):
        ticket_specs = [
            {
                "title": "Urgent billing issue",
                "description": "Customer reports payment failed and needs invoice help urgently.",
            },
            {
                "title": "Login access problem",
                "description": "User cannot access their account after changing email.",
            },
        ]
        tickets = []
        for spec in ticket_specs:
            ticket, _ = Ticket.objects.get_or_create(
                organization=organization,
                title=spec["title"],
                defaults={
                    "created_by": user,
                    "description": spec["description"],
                },
            )
            tickets.append(ticket)
            TicketComment.objects.get_or_create(
                ticket=ticket,
                author=user,
                content="Demo note: initial triage created for portfolio walkthrough.",
                defaults={"is_internal": True},
            )
        return tickets

    def _ensure_ticket_ai(self, tickets):
        for ticket in tickets:
            if not ticket.ai_summary:
                classify_ticket(ticket)
            ticket.refresh_from_db()
            if not ticket.ai_suggested_reply:
                suggest_ticket_reply(ticket)

    def _get_or_create_evaluation_case(self, *, user, organization, document):
        evaluation_case, _ = EvaluationCase.objects.get_or_create(
            organization=organization,
            question="How can a user reset their password?",
            defaults={
                "created_by": user,
                "expected_answer": "Users reset passwords from Account Settings using email verification.",
                "expected_document": document,
            },
        )
        if evaluation_case.expected_document_id is None:
            evaluation_case.expected_document = document
            evaluation_case.save(update_fields=["expected_document", "updated_at"])
        return evaluation_case

    def _ensure_evaluation_run(self, *, evaluation_case, user):
        if EvaluationRun.objects.filter(case=evaluation_case).exists():
            return
        run_evaluation_case(
            evaluation_case=evaluation_case,
            user=user,
            limit=5,
        )
