from django.contrib import admin

from .models import AnswerSource, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "created_at")
    fields = readonly_fields


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "user", "created_at", "updated_at")
    list_filter = ("organization", "created_at")
    search_fields = ("title", "organization__name", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("conversation__title", "content")
    readonly_fields = ("created_at",)


@admin.register(AnswerSource)
class AnswerSourceAdmin(admin.ModelAdmin):
    list_display = ("message", "document", "chunk", "score", "distance", "created_at")
    list_filter = ("document__organization", "created_at")
    search_fields = ("message__content", "document__title", "excerpt")
    readonly_fields = ("created_at",)
