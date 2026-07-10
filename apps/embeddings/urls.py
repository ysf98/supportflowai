from django.urls import path

from .views import SemanticSearchView

urlpatterns = [
    path("search/semantic/", SemanticSearchView.as_view(), name="semantic-search"),
]
