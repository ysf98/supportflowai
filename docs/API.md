# SupportFlow AI API

SupportFlow AI exposes a JWT-protected REST API documented with OpenAPI.

## Documentation

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

## Authentication

The API uses JWT authentication through SimpleJWT.

```txt
POST /api/auth/register/
POST /api/auth/token/
POST /api/auth/token/refresh/
GET  /api/users/me/
PATCH /api/users/me/
```

Use the access token as:

```txt
Authorization: Bearer <access-token>
```

## Pagination

List endpoints use page-number pagination.

Supported query parameters:

```txt
page=1
page_size=20
```

`page_size` is capped at 100.

## Filtering, Search, and Ordering

Main collection endpoints support a mix of:

- exact filters through `django-filter`,
- text search through `search`,
- ordering through `ordering`.

Examples:

```txt
GET /api/documents/?organization=1&status=processed
GET /api/tickets/?priority=urgent&ordering=-created_at
GET /api/conversations/?search=password
```

## Multi-Tenant Access

All organization-scoped querysets are filtered by the authenticated user's active organization memberships. A user cannot access resources from another organization by guessing IDs.

## Main Resource Groups

### Organizations

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

### Documents

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

### Semantic Search

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

### Chat RAG

```txt
GET    /api/conversations/
POST   /api/conversations/
GET    /api/conversations/{id}/
DELETE /api/conversations/{id}/
GET    /api/conversations/{id}/messages/
POST   /api/conversations/{id}/ask/
```

### Tickets

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

### Evaluations

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

### Dashboard

```txt
GET /api/dashboard/summary/
```

## AI Safety

Tests use `AI_PROVIDER=fake` and never call external AI services. RAG responses store sources separately in backend records.

## Async Endpoints

Long-running workflows expose explicit Celery-backed endpoints that return `202 Accepted` and a `task_id`.

```txt
POST /api/documents/{id}/process-async/
POST /api/documents/{id}/generate-embeddings-async/
POST /api/tickets/{id}/classify-async/
POST /api/tickets/{id}/suggest-reply-async/
POST /api/evaluation-cases/{id}/run-async/
```

The synchronous endpoints remain available for small/local workflows and service-level tests.

See `docs/ASYNC.md` for task details.

## Schema Validation

Validate OpenAPI with:

```bash
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
```
