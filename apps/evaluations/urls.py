from rest_framework.routers import DefaultRouter

from .views import EvaluationCaseViewSet, EvaluationRunViewSet

router = DefaultRouter()
router.register("evaluation-cases", EvaluationCaseViewSet, basename="evaluation-case")
router.register("evaluation-runs", EvaluationRunViewSet, basename="evaluation-run")

urlpatterns = router.urls
