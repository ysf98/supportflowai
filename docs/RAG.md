# SupportFlow AI RAG

SupportFlow AI implements Retrieval-Augmented Generation over organization documentation.

The goal is not to build a generic chatbot. The assistant answers internal support questions using only uploaded company documents and stores the sources used for each answer.

## Current Capabilities

- Upload `.txt` and `.md` documents.
- Extract UTF-8 text.
- Split text into deterministic chunks.
- Generate embeddings for chunks.
- Store embeddings in PostgreSQL with pgvector.
- Run semantic search filtered by organization.
- Ask questions in conversations.
- Generate answers with cited backend sources.
- Store user messages, assistant messages, and answer sources.
- Return a safe fallback when no relevant context exists.

## Data Flow

```txt
Document upload
      |
      v
Text extraction
      |
      v
Chunking
      |
      v
Embedding generation
      |
      v
pgvector search
      |
      v
RAG context
      |
      v
LLM answer
      |
      v
AnswerSource records
```

## Document Processing

Documents are stored in `Document`.

Supported formats:

- `.txt`
- `.md`

Processing creates `DocumentChunk` records with:

- chunk index,
- content,
- metadata,
- token count estimate,
- embedding status.

PDF support is intentionally deferred.

## Embeddings

Embeddings are stored on `DocumentChunk`.

Fields include:

- `embedding`,
- `embedding_model`,
- `embedding_provider`,
- `embedding_generated_at`,
- `embedding_status`,
- `embedding_error`.

Statuses:

```txt
pending
processing
ready
failed
```

Semantic search only uses chunks with `embedding_status=ready`.

## AI Providers

Providers are isolated behind `apps.ai.providers`.

### FakeAIProvider

Used for tests and local deterministic behavior.

Properties:

- deterministic embeddings,
- deterministic generated text,
- no external API calls,
- fixed dimensions from settings.

### OpenAIProvider

Prepared for real usage when configured with:

```txt
AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Provider errors are wrapped in application-specific exceptions.

## Technical Note About Dimensions

The project currently uses 16-dimensional embeddings for local development, fake provider behavior, and tests.

This is useful for proving architecture, permissions, services, and pgvector integration without depending on real embeddings.

Before using OpenAI embeddings in production, migrate `SUPPORTFLOW_EMBEDDING_DIMENSIONS` to a dimension compatible with the selected embedding model and create the required database migration.

## Semantic Search

Semantic search is implemented in `apps.embeddings.services.semantic_search`.

Steps:

1. validate non-empty query,
2. generate query embedding,
3. filter chunks by organization,
4. filter chunks with ready embeddings,
5. order by pgvector L2 distance,
6. return distance and derived score.

The organization filter is mandatory. Search never runs globally for normal users.

Endpoint:

```txt
POST /api/search/semantic/
```

Example:

```json
{
  "organization": 1,
  "query": "How can users reset their password?",
  "limit": 5
}
```

## Chat RAG Flow

Implemented in `apps.chat.services.ask_question`.

Flow:

1. validate user membership in conversation organization,
2. save user message,
3. run semantic search,
4. return safe fallback if no context exists,
5. build context from retrieved chunks,
6. build centralized prompt,
7. call AI provider,
8. save assistant message,
9. save `AnswerSource` records.

## Prompting

The RAG prompt lives in:

```txt
apps/chat/prompts.py
```

Prompt rules:

- answer only using provided context,
- say there is not enough information if context is insufficient,
- do not invent policies, links, or citations,
- keep answers clear and useful for support teams,
- sources are managed by the backend.

## Sources

Sources are stored as `AnswerSource`.

Each source links to:

- assistant message,
- document,
- chunk,
- score,
- distance,
- excerpt.

The backend stores citations independently from the LLM output. This avoids relying on the model to fabricate source labels.

## Safe Fallback

If no chunks are retrieved, the assistant stores:

```txt
I do not have enough information in the available documents to answer this question.
```

No sources are created in that case.

## Tests

RAG tests cover:

- conversation access,
- question flow,
- source creation,
- insufficient-context fallback,
- cross-organization source rejection,
- fake provider usage,
- no real OpenAI calls.

Run:

```bash
docker compose run --rm web pytest tests/chat tests/embeddings tests/ai
```

## Limitations

- No reranking yet.
- No hybrid keyword + vector search yet.
- No PDF parsing yet.
- No streaming responses.
- No task status polling UI yet.
- No production embedding migration has been applied for real OpenAI dimensions.

## Future Improvements

- Add reranking for top chunks.
- Add hybrid search.
- Add chunk overlap tuning per document type.
- Add PDF extraction.
- Add streaming chat responses.
- Add answer quality feedback from users.
- Track token usage and estimated cost per generation.
