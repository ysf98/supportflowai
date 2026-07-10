from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from apps.chat.models import Conversation
from apps.chat.services import ask_question, create_conversation
from apps.dashboard.services import build_dashboard_summary, get_accessible_organization_ids
from apps.documents.models import Document
from apps.documents.tasks import process_document_task
from apps.embeddings.services import EmbeddingPreconditionError
from apps.embeddings.tasks import generate_document_embeddings_task
from apps.evaluations.models import EvaluationCase, EvaluationRun
from apps.evaluations.tasks import run_evaluation_case_task
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import create_organization_with_owner
from apps.tickets.models import Ticket
from apps.tickets.services import resolve_ticket
from apps.tickets.tasks import classify_ticket_task, suggest_ticket_reply_task

from .forms import (
    AskQuestionForm,
    ConversationForm,
    DocumentUploadForm,
    EvaluationCaseForm,
    OrganizationForm,
    RegisterForm,
    RunEvaluationForm,
    TicketCommentForm,
    TicketForm,
)

User = get_user_model()


class WebLoginView(LoginView):
    template_name = "web/auth/login.html"
    redirect_authenticated_user = True


class WebLogoutView(LogoutView):
    next_page = reverse_lazy("web-login")


class RegisterView(FormView):
    template_name = "web/auth/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("web-dashboard")

    def form_valid(self, form):
        user = User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            name=form.cleaned_data["name"],
        )
        create_organization_with_owner(
            name=form.cleaned_data["organization_name"],
            owner=user,
        )
        login(self.request, user)
        messages.success(self.request, "Account and workspace created.")
        return redirect(self.success_url)


@login_required
def dashboard(request):
    organization_ids = get_accessible_organization_ids(request.user)
    context = {
        "summary": build_dashboard_summary(user=request.user),
        "recent_documents": Document.objects.filter(organization_id__in=organization_ids)[:5],
        "recent_tickets": Ticket.objects.filter(organization_id__in=organization_ids)[:5],
        "recent_conversations": Conversation.objects.filter(organization_id__in=organization_ids)[:5],
    }
    return render(request, "web/dashboard.html", context)


@login_required
def profile(request):
    memberships = OrganizationMembership.objects.filter(user=request.user, is_active=True).select_related("organization")
    return render(request, "web/profile.html", {"memberships": memberships})


@login_required
def organizations(request):
    organization_ids = get_accessible_organization_ids(request.user)
    form = OrganizationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_organization_with_owner(name=form.cleaned_data["name"], owner=request.user)
        messages.success(request, "Workspace created.")
        return redirect("web-organizations")
    return render(
        request,
        "web/organizations/list.html",
        {
            "organizations": Organization.objects.filter(id__in=organization_ids).prefetch_related("memberships"),
            "form": form,
        },
    )


@login_required
def documents(request):
    organization_ids = get_accessible_organization_ids(request.user)
    form = DocumentUploadForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        uploaded_file = form.cleaned_data["file"]
        document = form.save(commit=False)
        document.uploaded_by = request.user
        document.original_filename = uploaded_file.name
        document.content_type = getattr(uploaded_file, "content_type", "")
        document.size = uploaded_file.size
        document.save()
        messages.success(request, "Document uploaded.")
        return redirect("web-document-detail", pk=document.pk)
    return render(
        request,
        "web/documents/list.html",
        {
            "documents": Document.objects.filter(organization_id__in=organization_ids).annotate(chunk_count=Count("chunks")),
            "form": form,
        },
    )


@login_required
def document_detail(request, pk):
    organization_ids = get_accessible_organization_ids(request.user)
    document = get_object_or_404(
        Document.objects.filter(organization_id__in=organization_ids).annotate(chunk_count=Count("chunks")),
        pk=pk,
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "process":
            process_document_task.delay(document.id)
            messages.success(request, "Document processing queued.")
        elif action == "embed":
            try:
                if document.status != Document.Status.PROCESSED:
                    raise EmbeddingPreconditionError("Document must be processed before generating embeddings.")
                if not document.chunks.exists():
                    raise EmbeddingPreconditionError("Document has no chunks to embed.")
                generate_document_embeddings_task.delay(document.id)
                messages.success(request, "Embedding generation queued.")
            except EmbeddingPreconditionError as exc:
                messages.error(request, str(exc))
        return redirect("web-document-detail", pk=document.pk)
    return render(request, "web/documents/detail.html", {"document": document})


@login_required
def conversations(request):
    organization_ids = get_accessible_organization_ids(request.user)
    form = ConversationForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        conversation = create_conversation(
            user=request.user,
            organization=form.cleaned_data["organization"],
            title=form.cleaned_data["title"],
        )
        messages.success(request, "Conversation created.")
        return redirect("web-conversation-detail", pk=conversation.pk)
    return render(
        request,
        "web/chat/list.html",
        {
            "conversations": Conversation.objects.filter(organization_id__in=organization_ids).annotate(message_count=Count("messages")),
            "form": form,
        },
    )


@login_required
def conversation_detail(request, pk):
    organization_ids = get_accessible_organization_ids(request.user)
    conversation = get_object_or_404(Conversation.objects.filter(organization_id__in=organization_ids), pk=pk)
    form = AskQuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ask_question(
            conversation=conversation,
            user=request.user,
            question=form.cleaned_data["question"],
            limit=form.cleaned_data["limit"],
        )
        messages.success(request, "Question answered.")
        return redirect("web-conversation-detail", pk=conversation.pk)
    return render(
        request,
        "web/chat/detail.html",
        {
            "conversation": conversation,
            "messages": conversation.messages.prefetch_related("sources__document").all(),
            "form": form,
        },
    )


@login_required
def tickets(request):
    organization_ids = get_accessible_organization_ids(request.user)
    form = TicketForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.created_by = request.user
        ticket.save()
        messages.success(request, "Ticket created.")
        return redirect("web-ticket-detail", pk=ticket.pk)
    return render(
        request,
        "web/tickets/list.html",
        {
            "tickets": Ticket.objects.filter(organization_id__in=organization_ids).select_related("organization", "assigned_to"),
            "form": form,
        },
    )


@login_required
def ticket_detail(request, pk):
    organization_ids = get_accessible_organization_ids(request.user)
    ticket = get_object_or_404(Ticket.objects.filter(organization_id__in=organization_ids), pk=pk)
    comment_form = TicketCommentForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "comment":
            comment_form = TicketCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                comment.save()
                messages.success(request, "Comment added.")
        elif action == "classify":
            classify_ticket_task.delay(ticket.id)
            messages.success(request, "Ticket classification queued.")
        elif action == "suggest":
            suggest_ticket_reply_task.delay(ticket.id)
            messages.success(request, "Suggested reply generation queued.")
        elif action == "resolve":
            resolve_ticket(ticket=ticket, user=request.user, comment=request.POST.get("comment", ""))
            messages.success(request, "Ticket resolved.")
        return redirect("web-ticket-detail", pk=ticket.pk)
    return render(
        request,
        "web/tickets/detail.html",
        {
            "ticket": ticket,
            "comment_form": comment_form,
        },
    )


@login_required
def evaluations(request):
    organization_ids = get_accessible_organization_ids(request.user)
    form = EvaluationCaseForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        evaluation_case = form.save(commit=False)
        evaluation_case.created_by = request.user
        evaluation_case.save()
        messages.success(request, "Evaluation case created.")
        return redirect("web-evaluation-detail", pk=evaluation_case.pk)
    return render(
        request,
        "web/evaluations/list.html",
        {
            "cases": EvaluationCase.objects.filter(organization_id__in=organization_ids).select_related("organization", "expected_document"),
            "runs": EvaluationRun.objects.filter(organization_id__in=organization_ids)[:10],
            "form": form,
        },
    )


@login_required
def evaluation_detail(request, pk):
    organization_ids = get_accessible_organization_ids(request.user)
    evaluation_case = get_object_or_404(EvaluationCase.objects.filter(organization_id__in=organization_ids), pk=pk)
    form = RunEvaluationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        run_evaluation_case_task.delay(
            evaluation_case.id,
            request.user.id,
            form.cleaned_data["limit"],
        )
        messages.success(request, "Evaluation run queued.")
        return redirect("web-evaluation-detail", pk=evaluation_case.pk)
    return render(
        request,
        "web/evaluations/detail.html",
        {
            "case": evaluation_case,
            "runs": evaluation_case.runs.all(),
            "form": form,
        },
    )
