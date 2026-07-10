from django import forms
from django.contrib.auth import get_user_model

from apps.documents.models import Document
from apps.documents.services.extraction import validate_document_file
from apps.evaluations.models import EvaluationCase
from apps.organizations.models import Organization, OrganizationMembership
from apps.tickets.models import Ticket, TicketComment

User = get_user_model()


class RegisterForm(forms.Form):
    email = forms.EmailField()
    name = forms.CharField(max_length=255, required=False)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    organization_name = forms.CharField(max_length=255)

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name"]


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["organization", "title", "file"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations_for_user(user, minimum_role=OrganizationMembership.Role.ADMIN)

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        validate_document_file(uploaded_file)
        return uploaded_file


class ConversationForm(forms.Form):
    organization = forms.ModelChoiceField(queryset=Organization.objects.none())
    title = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations_for_user(user)


class AskQuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=2000)
    limit = forms.IntegerField(min_value=1, max_value=20, initial=5)


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["organization", "assigned_to", "title", "description", "status", "priority", "category"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations_for_user(user, minimum_role=OrganizationMembership.Role.AGENT)
        self.fields["assigned_to"].queryset = User.objects.filter(
            organization_memberships__organization__in=self.fields["organization"].queryset,
            organization_memberships__is_active=True,
        ).distinct()
        self.fields["assigned_to"].required = False


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["content", "is_internal"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3}),
        }


class EvaluationCaseForm(forms.ModelForm):
    class Meta:
        model = EvaluationCase
        fields = ["organization", "question", "expected_answer", "expected_document"]
        widgets = {
            "question": forms.Textarea(attrs={"rows": 3}),
            "expected_answer": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        orgs = organizations_for_user(user)
        self.fields["organization"].queryset = orgs
        self.fields["expected_document"].queryset = Document.objects.filter(organization__in=orgs)
        self.fields["expected_document"].required = False


class RunEvaluationForm(forms.Form):
    limit = forms.IntegerField(min_value=1, max_value=20, initial=5)


def organizations_for_user(user, minimum_role=None):
    if user is None or not user.is_authenticated:
        return Organization.objects.none()
    if user.is_superuser:
        return Organization.objects.all()
    queryset = Organization.objects.filter(memberships__user=user, memberships__is_active=True)
    if minimum_role:
        allowed_roles = {
            OrganizationMembership.Role.VIEWER: [
                OrganizationMembership.Role.VIEWER,
                OrganizationMembership.Role.AGENT,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.OWNER,
            ],
            OrganizationMembership.Role.AGENT: [
                OrganizationMembership.Role.AGENT,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.OWNER,
            ],
            OrganizationMembership.Role.ADMIN: [
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.OWNER,
            ],
            OrganizationMembership.Role.OWNER: [OrganizationMembership.Role.OWNER],
        }[minimum_role]
        queryset = queryset.filter(memberships__role__in=allowed_roles)
    return queryset.distinct()
