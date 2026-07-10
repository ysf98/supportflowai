# SupportFlow AI Testing Guide

SupportFlow AI uses `pytest` and `pytest-django` as the primary test stack.

The goal is not only line coverage. The suite is designed to prove the most important product guarantees:

- users only access organizations where they are members,
- roles gate mutating actions,
- RAG retrieval is organization-scoped,
- AI calls are mockable and never hit external services in tests,
- Celery tasks can run without a real worker in tests,
- OpenAPI remains valid and documents the main product endpoints.

## Test Settings

Tests run with:

```txt
DJANGO_SETTINGS_MODULE=config.settings.test
AI_PROVIDER=fake
CELERY_TASK_ALWAYS_EAGER=True
CELERY_TASK_EAGER_PROPAGATES=True
```

This means:

- Celery tasks execute in-process.
- Fake embeddings and fake text generation are deterministic.
- Tests do not call OpenAI or any external AI provider.
- Password hashing is faster through Django's MD5 test hasher.

## Test Areas

### Authentication and Users

Located in:

```txt
tests/users/
```

Covers registration, JWT login, token refresh, current user endpoint, and automatic initial organization creation.

### Organizations and Permissions

Located in:

```txt
tests/organizations/
tests/security/
```

Covers workspace membership, role boundaries, cross-organization access, and permission regressions for API and web views.

### Documents and Uploads

Located in:

```txt
tests/documents/
```

Covers upload validation, `.txt`/`.md` extraction, deterministic chunking, safe generated storage paths, size limits, empty file rejection, and malicious filename rejection.

### Embeddings and Semantic Search

Located in:

```txt
tests/embeddings/
tests/ai/
```

Covers fake provider determinism, embedding generation, failure handling, pgvector semantic search, organization filtering, and API access rules.

### Chat RAG

Located in:

```txt
tests/chat/
```

Covers conversations, messages, RAG answering, insufficient-context fallback, answer sources, and source isolation across organizations.

### Tickets

Located in:

```txt
tests/tickets/
```

Covers ticket CRUD, comments, state transitions, role permissions, AI classification, and suggested replies.

### Evaluations

Located in:

```txt
tests/evaluations/
```

Covers evaluation case creation, RAG evaluation runs, scoring rules, expected document matching, and organization filtering.

### Dashboard

Located in:

```txt
tests/dashboard/
```

Covers organization-scoped metrics and superuser global summary behavior.

### Async Tasks

Located in:

```txt
tests/async_tasks/
```

Covers Celery tasks for document processing, embeddings, ticket AI actions, and evaluation runs. Tasks run eagerly during tests.

### Web Interface

Located in:

```txt
tests/web/
```

Covers login redirects, registration, dashboard rendering, document upload, RAG questions, ticket actions, and evaluation runs.

### Demo Data

Located in:

```txt
tests/demo_data/
```

Covers the `seed_demo_data` management command and verifies that it creates a complete idempotent local demo dataset.

### API Contract and OpenAPI

Located in:

```txt
tests/api/
```

Covers pagination, filtering, search, ordering, schema availability, and required product endpoints in OpenAPI.

## Commands

Run the full suite:

```bash
docker compose run --rm web pytest
```

Run a focused area:

```bash
docker compose run --rm web pytest tests/security/
docker compose run --rm web pytest tests/chat/
docker compose run --rm web pytest tests/api/
```

Validate Django and migrations:

```bash
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
```

Validate OpenAPI:

```bash
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
```

## Continuous Integration

GitHub Actions runs the same core checks on pushes and pull requests to `main`.

Workflow:

```txt
.github/workflows/ci.yml
```

CI validates:

- Docker Compose configuration,
- image build,
- Django system checks,
- missing migrations,
- full pytest suite,
- OpenAPI schema,
- production-style deploy checks.

Production-style security check:

```bash
docker compose run --rm \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  -e SECRET_KEY=replace-with-a-long-random-secret \
  -e DEBUG=False \
  -e ALLOWED_HOSTS=localhost \
  -e CSRF_TRUSTED_ORIGINS=https://localhost \
  -e CORS_ALLOWED_ORIGINS=https://localhost \
  web python manage.py check --deploy
```

PowerShell equivalent:

```powershell
docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.production -e SECRET_KEY=replace-with-a-long-random-secret -e DEBUG=False -e ALLOWED_HOSTS=localhost -e CSRF_TRUSTED_ORIGINS=https://localhost -e CORS_ALLOWED_ORIGINS=https://localhost web python manage.py check --deploy
```

## Rules for Future Tests

- Do not call OpenAI or external services.
- Prefer service tests for business rules.
- Prefer API tests for permissions and multi-tenant isolation.
- Add regression tests for every bug fix.
- Keep tests deterministic.
- Test both success and denial paths for organization-scoped features.
