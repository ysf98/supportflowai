# SupportFlow AI - Agent Guide

## Project Name

SupportFlow AI

## Goal

Build a professional fullstack internal SaaS platform for enterprise support teams. The application will allow organizations to upload internal documentation, process documents, generate embeddings, ask RAG-based questions with cited sources, manage support tickets, classify incidents with AI, suggest replies, evaluate generated answers, and expose a documented REST API.

This project is designed for a professional portfolio and technical interviews. Prefer clarity, maintainability, testability, and explainable architecture over quick demos.

## Technical Stack

- Backend: Python, Django, Django REST Framework
- Database: PostgreSQL with pgvector
- Async: Celery with Redis
- Auth: SimpleJWT
- API docs: drf-spectacular / Swagger OpenAPI
- Filtering: django-filter
- Tests: pytest and pytest-django
- AI: OpenAI-compatible provider behind an abstraction
- Containers: Docker and Docker Compose
- Initial UI: Django Templates and Bootstrap 5 in a later phase

## Architecture

Use a modular Django monolith organized by business domains:

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
```

Keep views thin. Put business logic in services. Keep provider-specific AI code isolated behind interfaces.

## Main Decisions

- Use a custom user with email login starting in Phase 2.
- Every main business resource must belong to an organization.
- A user may belong to multiple organizations.
- Initial roles: owner, admin, agent, viewer.
- Registering a user will create an initial organization in Phase 2.
- Start with hard delete. Soft delete can be added later if needed.
- Start document parsing with `.txt` and `.md`. PDF support is a future improvement.
- Keep the frontend minimal until the backend, permissions, API, tests, and docs are solid.

## Security Rules

- Do not commit real secrets or `.env` files.
- Do not expose API keys in frontend code, logs, API responses, or tests.
- Production must not run with `DEBUG=True`.
- Production must require explicit `SECRET_KEY` and `ALLOWED_HOSTS`.
- Filter all organization-scoped querysets by the authenticated user's memberships.
- Never trust organization IDs from requests without validating membership and role.
- Do not expose internal tracebacks to end users.
- Validate uploaded files by extension, content type, and size when document upload is implemented.

## AI and RAG Rules

- Never call real OpenAI or external AI providers in tests.
- Use `FakeAIProvider` for tests and local deterministic behavior where appropriate.
- Use `OpenAIProvider` only through the shared AI abstraction.
- Keep prompts centralized and documented.
- RAG answers must include sources.
- If retrieved context is insufficient, the assistant must say it does not have enough information.
- Never invent unsupported answers.
- Always filter retrieval by organization.
- Use deterministic fake embeddings in tests.
- Log AI errors safely without secrets or raw stack traces in user-facing responses.

## Testing Conventions

- Use pytest and pytest-django.
- Prefer service tests for domain logic.
- Prefer API tests for permissions and multi-tenant isolation.
- Mock AI providers in all tests.
- Add regression tests for bugs.
- Test that organization A cannot access organization B resources.

## Documentation Conventions

- Keep documentation in English.
- Keep README practical and portfolio-ready.
- Use `docs/` for deeper architecture, API, RAG, testing, hardening, and portfolio notes in later phases.
- Keep OpenAPI valid with drf-spectacular.

## Main Commands

```bash
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web pytest
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
docker compose exec web celery -A config worker -l info
```

## Avoid

- Mixing business logic into views.
- Adding endpoints without permissions.
- Adding RAG without cited sources.
- Hardcoding prompts inside views.
- Calling real AI providers from tests.
- Building advanced frontend features before the backend is stable.
- Adding broad abstractions before the project needs them.
- Making unrelated refactors during a focused phase.
