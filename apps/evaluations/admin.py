from django.contrib import admin

from .models import EvaluationCase, EvaluationRun


class EvaluationRunInline(admin.TabularInline):
    model = EvaluationRun
    extra = 0
    readonly_fields = ("generated_answer", "score", "passed", "notes", "created_at", "updated_at")
    fields = readonly_fields


@admin.register(EvaluationCase)
class EvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ("question", "organization", "expected_document", "created_by", "created_at")
    list_filter = ("organization", "created_at")
    search_fields = ("question", "expected_answer", "organization__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [EvaluationRunInline]


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = ("case", "organization", "score", "passed", "created_at")
    list_filter = ("organization", "passed", "created_at")
    search_fields = ("case__question", "generated_answer", "notes")
    readonly_fields = (
        "generated_answer",
        "retrieved_sources",
        "score",
        "passed",
        "notes",
        "created_at",
        "updated_at",
    )
