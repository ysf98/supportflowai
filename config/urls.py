"""Root URL configuration for SupportFlow AI."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include("apps.web.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.organizations.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.embeddings.urls")),
    path("api/", include("apps.chat.urls")),
    path("api/", include("apps.tickets.urls")),
    path("api/", include("apps.evaluations.urls")),
    path("api/", include("apps.dashboard.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
