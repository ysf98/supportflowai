# SupportFlow AI

SupportFlow AI is a professional fullstack internal SaaS platform for enterprise support teams. It is designed to demonstrate a production-minded Django backend with multi-tenant organizations, REST APIs, AI-assisted support workflows, RAG over internal documentation, async processing, testing, Docker, and clear documentation.

## Status

Phase 16 completed: portfolio preparation.

The project currently includes:

- Django project structure
- Modular domain apps
- Environment-based settings
- Django REST Framework
- SimpleJWT
- drf-spectacular
- django-filter
- Celery worker configuration
- Redis broker/result backend configuration
- PostgreSQL with pgvector through Docker Compose
- pytest and pytest-django setup
- users, organizations, documents, embeddings, semantic search, and chat RAG
- tickets, evaluations, dashboard summary, Django Templates web UI, and async background jobs
- security-oriented settings, upload validation, and hardening documentation
- expanded professional test suite for permissions, serializers, OpenAPI, async tasks, web, and multi-tenant regressions
- idempotent demo data command for local portfolio walkthroughs
- portfolio-ready documentation, demo script, and screenshot checklist

## Stack

- Python
- Django
- Django REST Framework
- PostgreSQL + pgvector
- Redis
- Celery
- SimpleJWT
- drf-spectacular
- pytest + pytest-django
- pgvector-backed semantic search
- Docker and Docker Compose

## What This Project Demonstrates

- Multi-tenant SaaS-style backend with organizations and roles.
- Professional REST API design with DRF and OpenAPI.
- RAG over internal documentation with pgvector semantic search.
- AI provider abstraction with deterministic fake provider for tests.
- Celery/Redis background workflows.
- Server-rendered web UI for demos without Postman.
- Security hardening baseline.
- Professional pytest suite with 100+ tests.

## Feature Overview

- Email-based user registration and JWT login.
- Automatic initial organization on registration.
- Organization memberships with owner/admin/agent/viewer roles.
- Document upload for `.txt` and `.md`.
- Text extraction and deterministic chunking.
- Chunk embeddings stored in PostgreSQL with pgvector.
- Semantic search filtered by organization.
- RAG chat with stored answer sources.
- Support tickets with comments, status, priority, and category.
- AI ticket classification and suggested replies.
- Evaluation cases and RAG evaluation runs.
- Dashboard metrics.
- Celery-backed async endpoints.
- Professional Django Templates + Bootstrap web interface.

## Project Structure

```txt
apps/
  core/
  users/
  organizations/
  documents/
  embeddings/
  chat/
  tickets/
  ai/
  evaluations/
  dashboard/
  web/
config/
  settings/
docker/
requirements/
tests/
```

## Setup

Create a local environment file:

```bash
cp .env.example .env
```

Build and start the stack:

```bash
docker compose up --build
```

Run checks:

```bash
docker compose run --rm web python manage.py check
docker compose run --rm web pytest
```

Seed demo data:

```bash
docker compose run --rm web python manage.py seed_demo_data
```

Default demo credentials:

```txt
demo@example.com
DemoPass123!
```

## Useful Commands

```bash
docker compose config
docker compose build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web pytest
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
docker compose exec worker celery -A config inspect ping
```

## API Docs

When the development server is running:

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

Additional API notes live in `docs/API.md`.

Asynchronous processing is documented in `docs/ASYNC.md`.

Security hardening is documented in `docs/HARDENING.md`.

Testing strategy is documented in `docs/TESTING.md`.

Architecture is documented in `docs/ARCHITECTURE.md`.

RAG design is documented in `docs/RAG.md`.

Business rules are documented in `docs/BUSINESS_RULES.md`.

Portfolio guidance is documented in `docs/PORTFOLIO.md`.

Demo data is documented in `docs/DEMO_DATA.md`.

## Web Interface

When the development server is running:

- Web app: `/`
- Login: `/login/`
- Register: `/register/`
- API docs: `/api/docs/`

The web interface is documented in `docs/WEB.md`.

## Current API Endpoints

Authentication:

```txt
POST /api/auth/register/
POST /api/auth/token/
POST /api/auth/token/refresh/
GET  /api/users/me/
PATCH /api/users/me/
```

Organizations:

```txt
GET    /api/organizations/
POST   /api/organizations/
GET    /api/organizations/{id}/
PATCH  /api/organizations/{id}/
DELETE /api/organizations/{id}/
GET    /api/organizations/{id}/members/
POST   /api/organizations/{id}/members/
PATCH  /api/organizations/{id}/members/{member_id}/
DELETE /api/organizations/{id}/members/{member_id}/
```

Documents:

```txt
GET    /api/documents/
POST   /api/documents/
GET    /api/documents/{id}/
PATCH  /api/documents/{id}/
DELETE /api/documents/{id}/
GET    /api/documents/{id}/chunks/
POST   /api/documents/{id}/process/
POST   /api/documents/{id}/process-async/
POST   /api/documents/{id}/generate-embeddings/
POST   /api/documents/{id}/generate-embeddings-async/
```

Semantic search:

```txt
POST /api/search/semantic/
```

Chat RAG:

```txt
GET    /api/conversations/
POST   /api/conversations/
GET    /api/conversations/{id}/
DELETE /api/conversations/{id}/
GET    /api/conversations/{id}/messages/
POST   /api/conversations/{id}/ask/
```

Tickets:

```txt
GET    /api/tickets/
POST   /api/tickets/
GET    /api/tickets/{id}/
PATCH  /api/tickets/{id}/
DELETE /api/tickets/{id}/
POST   /api/tickets/{id}/comments/
POST   /api/tickets/{id}/classify/
POST   /api/tickets/{id}/classify-async/
POST   /api/tickets/{id}/suggest-reply/
POST   /api/tickets/{id}/suggest-reply-async/
POST   /api/tickets/{id}/resolve/
```

Evaluations:

```txt
GET    /api/evaluation-cases/
POST   /api/evaluation-cases/
GET    /api/evaluation-cases/{id}/
PATCH  /api/evaluation-cases/{id}/
DELETE /api/evaluation-cases/{id}/
POST   /api/evaluation-cases/{id}/run/
POST   /api/evaluation-cases/{id}/run-async/
GET    /api/evaluation-runs/
GET    /api/evaluation-runs/{id}/
```

Dashboard:

```txt
GET /api/dashboard/summary/
```

Example search payload:

```json
{
  "organization": 1,
  "query": "How do I reset my password?",
  "limit": 5
}
```

## AI and Embeddings

SupportFlow AI uses an AI provider abstraction:

- `FakeAIProvider` returns deterministic local embeddings for development and tests.
- `OpenAIProvider` is prepared for real embeddings when `AI_PROVIDER=openai` and `OPENAI_API_KEY` are configured.
- Tests force the fake provider and never call external AI services.
- Semantic search uses pgvector and always filters by organization.
- Chat RAG stores conversations, user messages, assistant answers, and cited sources.
- Assistant answers are generated from retrieved chunks; if no context is found, the system returns a safe insufficient-information response.
- Ticket AI services can classify category/priority, summarize tickets, and suggest support replies.
- Evaluation cases can run RAG questions and store generated answers, retrieved sources, scores, and pass/fail results.
- Dashboard summary exposes organization-scoped counts for documents, chunks, conversations, tickets, evaluations, and estimated AI operations.
- Celery tasks can process documents, generate embeddings, classify tickets, suggest ticket replies, and run evaluations in the background.

## Async Processing

The project uses Celery with Redis for background jobs. The synchronous service layer remains the source of truth, while Celery tasks wrap those services for longer-running workflows.

Current task coverage:

- Document processing and chunk generation.
- Document embedding generation.
- Pending organization embedding generation.
- Ticket classification.
- Ticket reply suggestion.
- Evaluation case execution.

The web interface queues these operations where appropriate. The API exposes both synchronous endpoints and explicit `*-async` endpoints that return `202 Accepted` with a Celery `task_id`.

Relevant environment variables:

```txt
AI_PROVIDER=fake
SUPPORTFLOW_EMBEDDING_DIMENSIONS=16
FAKE_EMBEDDING_DIMENSIONS=16
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SUPPORTFLOW_MAX_UPLOAD_SIZE=5242880
```

Technical note: the project currently uses 16-dimensional embeddings for development, the fake provider, and tests. Before using OpenAI embeddings in production, migrate to a dimension compatible with the selected real embedding model.

## Demo Flow

1. Register or log in.
2. Open the dashboard.
3. Upload a `.txt` or `.md` document.
4. Queue document processing.
5. Queue embedding generation.
6. Create a RAG conversation and ask a question.
7. Inspect answer sources.
8. Create a support ticket.
9. Queue classification and suggested reply.
10. Create and run an evaluation case.

For a faster walkthrough, run:

```bash
docker compose run --rm web python manage.py seed_demo_data
```

Then log in with `demo@example.com` / `DemoPass123!`.

## Current Limitations

- Fake/local embeddings use 16 dimensions.
- Real OpenAI embeddings require a dimension migration before production use.
- PDF parsing is planned but not implemented.
- Task status polling UI is not implemented yet.
- Rate limiting and audit logs are documented as future hardening improvements.
- Demo data seeding is available for local development.

## Documentation Map

```txt
docs/ARCHITECTURE.md     system design and app boundaries
docs/API.md              REST API notes and endpoint groups
docs/RAG.md              RAG, embeddings, prompts, sources
docs/BUSINESS_RULES.md   roles, permissions, statuses, workflows
docs/ASYNC.md            Celery/Redis background processing
docs/WEB.md              server-rendered UI
docs/TESTING.md          testing strategy and commands
docs/HARDENING.md        security baseline
docs/PORTFOLIO.md        interview/demo guide
docs/DEMO_DATA.md        local demo seed command
```

## Portfolio Summary

Suggested CV bullet:

```txt
Built SupportFlow AI, a Django/DRF internal support SaaS platform with organization-based permissions, document ingestion, pgvector semantic search, RAG answers with cited sources, AI-assisted ticket workflows, Celery background tasks, dashboard metrics, OpenAPI docs, Docker setup, and 100+ automated tests.
```

Best files to discuss in interviews:

```txt
apps/chat/services.py
apps/ai/providers.py
apps/embeddings/services.py
apps/documents/services/processing.py
apps/tickets/services.py
apps/evaluations/services.py
apps/organizations/permissions.py
tests/security/test_permission_regressions.py
tests/api/test_api_contract.py
```

See `docs/PORTFOLIO.md` for the full demo script and screenshot checklist.

## Roadmap

1. Users, organizations, memberships, and permissions
2. Document upload, text extraction, and chunking
3. Embeddings and semantic search with pgvector
4. RAG chat with cited sources
5. AI-assisted support tickets
6. Evaluation module
7. Dashboard metrics
8. Web UI with Django Templates and Bootstrap 5
9. Celery-backed async workflows
10. Security hardening baseline
11. Professional testing expansion
12. Professional documentation expansion
13. Demo data command
14. Portfolio polish and screenshots
15. Optional future enhancements: task polling, rate limiting, PDF parsing, audit logs
