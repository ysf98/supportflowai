import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from .models import EvaluationCase
from .services import run_evaluation_case

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_evaluation_case_task(self, evaluation_case_id: int, user_id: int, limit: int = 5) -> dict:
    User = get_user_model()
    evaluation_case = EvaluationCase.objects.get(pk=evaluation_case_id)
    user = User.objects.get(pk=user_id)
    logger.info(
        "Running evaluation case %s with task %s.",
        evaluation_case_id,
        self.request.id,
    )
    evaluation_run = run_evaluation_case(
        evaluation_case=evaluation_case,
        user=user,
        limit=limit,
    )
    return {
        "evaluation_case_id": evaluation_case.id,
        "evaluation_run_id": evaluation_run.id,
        "score": evaluation_run.score,
        "passed": evaluation_run.passed,
    }
