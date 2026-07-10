# SupportFlow AI Architecture

SupportFlow AI is a modular Django monolith for internal enterprise support workflows.

The project intentionally avoids microservices at this stage. A modular monolith is easier to run locally, easier to test end to end, and still demonstrates clean domain boundaries.

## High-Level Overview

```txt
Browser / API client
        |
        v
Django Web UI + Django REST Framework
        |
        v
Domain services
        |
        +--> PostgreSQL + pgvector
        +--> Redis + Celery
        +--> AI provider abstraction
```

## Main Building Blocks

### Django Apps

```txt
apps/
  core/           shared base models, pagination, serializers, permissions
  users/          custom user, registration, JWT auth, current user API
  organizations/  workspaces, memberships, roles, tenant boundaries
  documents/      document upload, validation, extraction, chunking
  embeddings/     embedding generation and semantic search
  chat/           RAG conversations, messages, answer sources
  tickets/        support tickets, comments, AI classification, reply suggestions
  ai/             provider abstraction, fake provider, OpenAI provider
  evaluations/    RAG evaluation cases and runs
  dashboard/      organization-scoped metrics
  web/            server-rendered UI with Django Templates
```

### Settings

Settings are split by environment:

```txt
config/settings/base.py
config/settings/development.py
config/settings/production.py
config/settings/test.py
```

`base.py` contains shared configuration. Production adds HTTPS, cookie, CSRF, CORS, and secret validation. Tests force fake AI and eager Celery tasks.

## Architectural Layers

### Models

Models represent persistent business state:

- users,
- organizations and memberships,
- documents and chunks,
- conversations, messages, answer sources,
- tickets and comments,
- evaluation cases and runs.

Most business resources are organization-scoped.

### Serializers

Serializers validate API input and output shapes.

They enforce boundaries such as:

- a user cannot create resources in an organization where they are not a member,
- evaluation expected documents must belong to the same organization,
- RAG limits are bounded,
- fields like `created_by` and `uploaded_by` are not user-controlled.

### Views

API views and web views stay thin.

They handle:

- authentication,
- request/response formatting,
- object lookup,
- permission checks,
- calling domain services or Celery tasks.

Business logic belongs in services, not views.

### Domain Services

Services hold the core workflows:

- document processing,
- text chunking,
- embedding generation,
- semantic search,
- RAG answering,
- ticket classification,
- suggested replies,
- evaluation scoring,
- dashboard summaries.

This makes the code easier to test and easier to explain in interviews.

### Celery Tasks

Celery tasks wrap domain services for longer-running work:

- document processing,
- embedding generation,
- ticket AI actions,
- evaluation runs.

Tasks load records by ID, call services, and return compact metadata. The synchronous service layer remains the source of truth.

## Data Model Summary

### Users and Organizations

```txt
User
  -> OrganizationMembership
       -> Organization
```

Users can belong to multiple organizations. Roles are:

- owner,
- admin,
- agent,
- viewer.

### Documents and Chunks

```txt
Organization
  -> Document
       -> DocumentChunk
```

Documents are uploaded as `.txt` or `.md`, extracted to text, split into deterministic chunks, and optionally embedded.

### RAG Chat

```txt
Organization
  -> Conversation
       -> Message
            -> AnswerSource
                 -> Document
                 -> DocumentChunk
```

Assistant messages store sources separately instead of relying on the LLM to invent citations.

### Tickets

```txt
Organization
  -> Ticket
       -> TicketComment
```

Tickets can be classified and enriched with AI-generated support replies.

### Evaluations

```txt
Organization
  -> EvaluationCase
       -> EvaluationRun
```

Evaluation runs execute RAG questions and score basic quality criteria.

## Multi-Tenancy

The application uses organization-based multi-tenancy.

Rules:

- every main resource belongs to an organization,
- querysets are filtered by active memberships,
- users cannot access resources by guessing IDs,
- role checks gate mutating actions,
- superusers can access global data for administration.

This is tested across API, web, services, and serializers.

## AI Provider Design

AI is isolated behind `apps.ai.providers`.

Providers:

- `FakeAIProvider`: deterministic embeddings and text generation for tests/local development.
- `OpenAIProvider`: prepared for real OpenAI-compatible calls.

Tests never call external AI services.

## RAG Design

RAG is implemented as:

1. user asks a question in a conversation,
2. question is embedded,
3. semantic search retrieves organization-filtered chunks,
4. context is built from retrieved excerpts,
5. provider generates an answer,
6. answer and sources are saved.

If no context is available, the system stores a safe insufficient-information answer.

## Deployment Shape

Local development runs with Docker Compose:

```txt
web      Django development server
worker   Celery worker
db       PostgreSQL with pgvector
redis    Redis broker/result backend
```

Production would replace the dev server with Gunicorn or a platform equivalent, keep PostgreSQL + pgvector, and run Celery workers separately.

## Key Decisions

- Modular monolith over microservices.
- Django Templates first for a complete demo without frontend complexity.
- Services-first domain logic.
- Fake AI provider for deterministic tests.
- Explicit async endpoints instead of hiding background behavior.
- Hard delete for now; soft delete is future work.
- `.txt` and `.md` parsing first; PDF parsing is future work.

## Future Architecture Improvements

- Task status polling API.
- Audit log model for sensitive changes.
- Rate limiting.
- Object storage for uploads.
- PDF parsing pipeline.
- Production-ready file scanning.
- Optional Next.js frontend once backend is complete.
