from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="web-dashboard"),
    path("login/", views.WebLoginView.as_view(), name="web-login"),
    path("logout/", views.WebLogoutView.as_view(), name="web-logout"),
    path("register/", views.RegisterView.as_view(), name="web-register"),
    path("profile/", views.profile, name="web-profile"),
    path("organizations/", views.organizations, name="web-organizations"),
    path("documents/", views.documents, name="web-documents"),
    path("documents/<int:pk>/", views.document_detail, name="web-document-detail"),
    path("chat/", views.conversations, name="web-conversations"),
    path("chat/<int:pk>/", views.conversation_detail, name="web-conversation-detail"),
    path("tickets/", views.tickets, name="web-tickets"),
    path("tickets/<int:pk>/", views.ticket_detail, name="web-ticket-detail"),
    path("evaluations/", views.evaluations, name="web-evaluations"),
    path("evaluations/<int:pk>/", views.evaluation_detail, name="web-evaluation-detail"),
]
