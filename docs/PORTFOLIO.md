# SupportFlow AI Portfolio Guide

SupportFlow AI is designed as a portfolio project for backend/fullstack interviews.

It demonstrates a realistic internal SaaS platform for support teams, not a simple chatbot demo.

## One-Line CV Description

SupportFlow AI - Internal support SaaS platform with Django, DRF, PostgreSQL/pgvector, Celery, Redis, JWT auth, organization roles, document processing, RAG answers with cited sources, AI-assisted ticket workflows, evaluation runs, dashboard metrics, tests, Docker, and OpenAPI documentation.

## Short Interview Pitch

SupportFlow AI is a modular Django SaaS-style application for enterprise support teams. Companies can upload internal documentation, generate embeddings, ask RAG questions with sources, manage tickets, classify issues with AI, generate suggested replies, evaluate answer quality, and inspect organization-scoped metrics.

The project focuses on backend architecture, multi-tenant permissions, AI abstraction, RAG, async processing, testing, documentation, and a usable server-rendered web interface.

## What This Project Demonstrates

### Backend Engineering

- Django project structure.
- Modular domain apps.
- Django REST Framework APIs.
- Serializers and validation.
- ViewSets and custom actions.
- Service-layer business logic.
- PostgreSQL data modeling.
- pgvector semantic search.
- Celery background processing.
- Redis broker/result backend.

### SaaS Concepts

- Custom user model.
- Email login.
- Organizations/workspaces.
- Memberships.
- Roles and permissions.
- Multi-tenant data isolation.
- Dashboard metrics.

### AI Engineering

- AI provider abstraction.
- Deterministic fake AI provider.
- OpenAI provider prepared.
- Embeddings.
- Semantic search.
- RAG prompt centralization.
- Answers with backend-stored sources.
- Safe insufficient-context fallback.
- AI-assisted ticket classification and reply suggestions.
- Basic RAG evaluation module.

### Quality and Delivery

- Docker Compose setup.
- Environment-based settings.
- Security hardening baseline.
- Automated tests with pytest.
- GitHub Actions CI.
- OpenAPI documentation.
- Professional docs in `docs/`.
- Server-rendered UI for demo without Postman.

## Demo Flow

### 1. Seed Data, Register, or Log In

For the fastest demo, run:

```bash
docker compose run --rm web python manage.py seed_demo_data
```

This creates a complete local walkthrough dataset.

Use:

```txt
/register/
/login/
```

Registration creates an initial organization automatically.

Demo account:

```txt
demo@example.com
DemoPass123!
```

### 2. Show Dashboard

Open:

```txt
/
```

Explain:

- organization-scoped metrics,
- documents,
- chunks,
- tickets,
- conversations,
- evaluations,
- estimated AI operations.

### 3. Upload Documentation

Open:

```txt
/documents/
```

Upload a `.txt` or `.md` file.

Then open the document detail and queue:

- processing,
- embedding generation.

Explain:

- file validation,
- text extraction,
- deterministic chunking,
- pgvector embeddings,
- Celery async workflows.

### 4. Ask a RAG Question

Open:

```txt
/chat/
```

Create a conversation and ask a question based on uploaded docs.

Show:

- user message,
- assistant answer,
- sources,
- document titles,
- scores.

Explain:

- retrieval is organization-scoped,
- prompts are centralized,
- sources are backend records,
- no context means safe fallback.

### 5. Manage Tickets

Open:

```txt
/tickets/
```

Create a ticket.

From ticket detail:

- queue classification,
- queue suggested reply,
- add comment,
- resolve ticket.

Explain:

- role-based access,
- AI-assisted triage,
- background task processing,
- stored AI summary and suggested reply.

### 6. Run Evaluations

Open:

```txt
/evaluations/
```

Create an evaluation case with:

- question,
- expected answer,
- optional expected document.

Queue a run.

Explain:

- RAG answer quality checks,
- source matching,
- simple scoring,
- pass/fail results.

### 7. Show API Docs

Open:

```txt
/api/docs/
```

Show:

- JWT auth endpoints,
- organizations,
- documents,
- semantic search,
- conversations,
- tickets,
- evaluations,
- dashboard,
- async endpoints.

## Interview Talking Points

### Why Django?

Django provides strong primitives for a SaaS-style backend: ORM, auth, admin, forms, sessions, testing, and mature ecosystem support.

### Why a Modular Monolith?

The project has clear domain boundaries without operational complexity. It is realistic for a small team and still easy to evolve.

### Why Django Templates First?

The priority is backend depth, permissions, RAG, async processing, tests, and docs. Templates provide a usable demo interface without delaying backend quality.

### Why FakeAIProvider?

AI code must be testable and deterministic. The fake provider allows tests to verify behavior without external API calls, cost, latency, or flakiness.

### How Is Multi-Tenancy Enforced?

Every main resource belongs to an organization. Querysets filter by active memberships, serializers validate organization access, and services enforce role/membership boundaries.

### How Are Sources Handled?

Sources are stored in `AnswerSource` records linked to assistant messages, documents, and chunks. The model does not rely on the LLM to invent citations.

### How Does Async Work?

Celery tasks wrap domain services. The services remain testable and synchronous, while API/web endpoints can queue longer-running operations.

## Strong Files to Show

```txt
apps/chat/services.py
apps/chat/prompts.py
apps/ai/providers.py
apps/embeddings/services.py
apps/documents/services/processing.py
apps/tickets/services.py
apps/evaluations/services.py
apps/organizations/permissions.py
config/settings/production.py
tests/security/test_permission_regressions.py
tests/serializers/test_serializer_boundaries.py
tests/api/test_api_contract.py
```

## Commands to Demonstrate

```bash
docker compose up --build
docker compose exec web python manage.py migrate
docker compose run --rm web python manage.py seed_demo_data
docker compose run --rm web pytest
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
```

## Recommended Screenshots

Use these screenshots for GitHub, LinkedIn, or a portfolio page:

1. `docs/screenshots/dashboard.png` - Dashboard with seeded metrics.
2. `docs/screenshots/documents.png` - Document list and processing actions.
3. `docs/screenshots/document-detail.png` - Processed document detail and chunks.
4. `docs/screenshots/chat.png` - RAG conversation with answer sources.
5. `docs/screenshots/ticket.png` - Ticket detail with status, priority, AI summary, and suggested reply.
6. `docs/screenshots/evaluation.png` - Evaluation detail with run score and notes.
7. `docs/screenshots/api-docs.png` - Swagger UI with grouped API endpoints.
8. A terminal screenshot showing `pytest` and GitHub Actions passing.

Regenerate browser screenshots locally with:

```bash
node scripts/capture_screenshots.mjs
```

The command expects the Docker stack to be running and demo data to exist.

## Demo Script

Use this short script in an interview:

1. "This is a modular Django SaaS-style project for internal support teams."
2. "Users belong to organizations through memberships, and every main resource is organization-scoped."
3. "A company uploads support documentation, the backend extracts text, chunks it, generates embeddings, and stores them in pgvector."
4. "The chat flow retrieves relevant chunks, builds a prompt, generates an answer, and stores sources as backend records."
5. "Tickets can be classified and enriched with AI-generated replies through services and Celery tasks."
6. "Evaluations run RAG questions and score answer/source quality."
7. "The test suite uses a deterministic fake AI provider, so tests never call OpenAI."
8. "The project includes Docker, OpenAPI, hardening docs, and a web UI for live demos."

## Current Limitations

- Embedding dimension is 16 for fake/local development.
- Real OpenAI production embeddings require a dimension migration.
- PDF parsing is not implemented yet.
- No task status polling UI yet.
- No rate limiting yet.
- No audit log model yet.
- No production object storage yet.
- No email notification workflow yet.

## Future Improvements

- Screenshots and GIF walkthrough.
- Task status UI.
- PDF parsing.
- Rate limiting.
- Audit logs.
- Object storage.
- Reranking for RAG.
- Hybrid search.
- Cost tracking per AI call.
- Optional Next.js frontend.

## Suggested GitHub README Highlights

- "Multi-tenant Django SaaS architecture"
- "RAG with pgvector and cited sources"
- "AI provider abstraction with deterministic fake provider"
- "Celery/Redis async workflows"
- "Professional pytest suite"
- "OpenAPI documented REST API"
- "Server-rendered Bootstrap UI for demos"

## Suggested CV Bullet

Built SupportFlow AI, a Django/DRF internal support SaaS platform with organization-based permissions, document ingestion, pgvector semantic search, RAG answers with cited sources, AI-assisted ticket workflows, Celery background tasks, dashboard metrics, OpenAPI docs, Docker setup, and 100+ automated tests.
