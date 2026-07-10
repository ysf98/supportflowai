from django.contrib import admin

from .models import Ticket, TicketComment


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ("author", "content", "is_internal", "created_at", "updated_at")
    fields = readonly_fields


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status", "priority", "category", "assigned_to", "created_at")
    list_filter = ("status", "priority", "category", "organization")
    search_fields = ("title", "description", "ai_summary", "organization__name")
    readonly_fields = ("ai_summary", "ai_suggested_reply", "created_at", "updated_at")
    inlines = [TicketCommentInline]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal", "created_at")
    search_fields = ("ticket__title", "content", "author__email")
    readonly_fields = ("created_at", "updated_at")
