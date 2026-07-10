from dataclasses import dataclass

from django.db import transaction

from apps.ai.exceptions import AIProviderError
from apps.ai.providers import get_ai_provider
from apps.embeddings.services import SemanticSearchResult, semantic_search
from apps.organizations.permissions import get_user_role

from .models import AnswerSource, Conversation, Message
from .prompts import build_rag_prompt


INSUFFICIENT_CONTEXT_MESSAGE = (
    "I do not have enough information in the available documents to answer this question."
)


class ChatPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class AskQuestionResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    sources: list[AnswerSource]


def ensure_conversation_access(*, user, conversation: Conversation) -> None:
    if get_user_role(user, conversation.organization) is None:
        raise ChatPermissionError("You cannot access this conversation.")


def create_conversation(*, user, organization, title: str | None = None) -> Conversation:
    if get_user_role(user, organization) is None:
        raise ChatPermissionError("You cannot create a conversation in this organization.")

    clean_title = (title or "").strip() or "New conversation"
    return Conversation.objects.create(
        organization=organization,
        user=user,
        title=clean_title,
    )


def build_rag_context(search_results: list[SemanticSearchResult]) -> str:
    context_blocks = []
    for index, result in enumerate(search_results, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"Source {index}",
                    f"Document: {result.document_title}",
                    f"Chunk: {result.chunk_index}",
                    f"Excerpt: {result.excerpt}",
                ]
            )
        )
    return "\n\n".join(context_blocks)


def generate_rag_answer(*, question: str, context: str) -> str:
    if not context.strip():
        return INSUFFICIENT_CONTEXT_MESSAGE

    provider = get_ai_provider()
    prompt = build_rag_prompt(question=question, context=context)
    return provider.generate_text(prompt=prompt, question=question, context=context)


def save_answer_sources(
    *,
    message: Message,
    search_results: list[SemanticSearchResult],
) -> list[AnswerSource]:
    conversation_org_id = message.conversation.organization_id
    sources = []

    for result in search_results:
        if result.document_organization_id != conversation_org_id:
            continue
        if result.chunk_organization_id != conversation_org_id:
            continue
        sources.append(
            AnswerSource(
                message=message,
                document_id=result.document_id,
                chunk_id=result.chunk_id,
                distance=result.distance,
                score=result.score,
                excerpt=result.excerpt,
            )
        )

    return AnswerSource.objects.bulk_create(sources)


def ask_question(
    *,
    conversation: Conversation,
    user,
    question: str,
    limit: int = 5,
) -> AskQuestionResult:
    ensure_conversation_access(user=user, conversation=conversation)

    clean_question = question.strip()
    with transaction.atomic():
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=clean_question,
        )

    search_results = semantic_search(
        organization=conversation.organization,
        query=clean_question,
        limit=limit,
    )

    if not search_results:
        assistant_content = INSUFFICIENT_CONTEXT_MESSAGE
        with transaction.atomic():
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=assistant_content,
            )
            conversation.save(update_fields=["updated_at"])
        return AskQuestionResult(conversation, user_message, assistant_message, [])

    context = build_rag_context(search_results)
    try:
        assistant_content = generate_rag_answer(question=clean_question, context=context)
    except AIProviderError:
        raise

    with transaction.atomic():
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=assistant_content,
        )
        sources = save_answer_sources(message=assistant_message, search_results=search_results)
        conversation.save(update_fields=["updated_at"])

    return AskQuestionResult(conversation, user_message, assistant_message, sources)
