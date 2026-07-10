from django.conf import settings
from django.db import models

from apps.core.models import OrganizationScopedModel


class EvaluationCase(OrganizationScopedModel):
    question = models.TextField()
    expected_answer = models.TextField(blank=True)
    expected_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        related_name="evaluation_cases",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluation_cases",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:80]


class EvaluationRun(OrganizationScopedModel):
    case = models.ForeignKey(
        EvaluationCase,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    generated_answer = models.TextField()
    retrieved_sources = models.JSONField(default=list, blank=True)
    score = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Evaluation run {self.id} for case {self.case_id}"
