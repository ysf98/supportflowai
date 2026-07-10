# SupportFlow AI Hardening Guide

This document summarizes the current security posture of SupportFlow AI and the rules to follow before running it outside local development.

## Implemented Controls

### Secrets and Environment

- Real secrets are not committed.
- `.env.example` contains placeholders only.
- Production settings fail fast when `SECRET_KEY` is not configured safely.
- Production settings reject `DEBUG=True`.
- Production settings reject wildcard `ALLOWED_HOSTS`.

### Hosts, CORS, and CSRF

- `ALLOWED_HOSTS` is environment-driven.
- `CORS_ALLOW_ALL_ORIGINS` is disabled by default.
- `CORS_ALLOWED_ORIGINS` is configured through environment variables.
- `CSRF_TRUSTED_ORIGINS` is configured through environment variables.
- Production requires `CSRF_TRUSTED_ORIGINS`.

### HTTPS and Browser Security

Production settings enable:

- HTTPS redirect.
- Secure session cookies.
- Secure CSRF cookies.
- `SameSite=Lax` cookies.
- HSTS with subdomains and preload.
- `X_FRAME_OPTIONS = "DENY"`.
- `SECURE_CONTENT_TYPE_NOSNIFF = True`.
- `REFERRER_POLICY = "same-origin"`.

### Authentication

- API authentication uses JWT through SimpleJWT.
- Web authentication uses Django sessions.
- Passwords are hashed through Django's authentication system.
- Registration creates an initial organization with owner membership.

### Multi-Tenant Isolation

- Business resources are scoped to organizations.
- Querysets filter by active organization memberships.
- Role checks gate mutating actions.
- Users cannot access resources from organizations where they are not members.
- Tests cover cross-organization access for major domains.

### Upload Safety

- Supported document types are limited to `.txt` and `.md`.
- Content types are validated.
- Upload size is capped by `SUPPORTFLOW_MAX_UPLOAD_SIZE`.
- Empty files are rejected.
- Filenames containing path separators are rejected.
- Stored file paths use generated UUID names instead of original filenames.
- Original filenames are stored as metadata for display/audit.

### AI Safety

- AI calls go through provider abstractions.
- Tests force `FakeAIProvider`.
- Tests never call OpenAI or external providers.
- API keys are read from environment variables only.
- RAG retrieval is organization-filtered.
- RAG answers store sources separately.
- When context is insufficient, the assistant returns a safe fallback response.

### Async Safety

- Celery tasks load resources by ID and call domain services.
- Tests run Celery tasks eagerly and in-process.
- Worker logs use compact metadata and avoid secrets.

## Required Production Variables

At minimum:

```txt
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<strong-random-secret>
DEBUG=False
ALLOWED_HOSTS=supportflow.example.com
CSRF_TRUSTED_ORIGINS=https://supportflow.example.com
CORS_ALLOWED_ORIGINS=https://supportflow.example.com
DATABASE_URL=<production-postgres-url>
REDIS_URL=<production-redis-url>
CELERY_BROKER_URL=<production-redis-url>
CELERY_RESULT_BACKEND=<production-redis-result-url>
AI_PROVIDER=fake|openai
OPENAI_API_KEY=<only-if-using-openai>
```

## Verification Commands

```bash
docker compose run --rm web python manage.py check --deploy
docker compose run --rm web python manage.py test
docker compose run --rm web pytest
docker compose run --rm web python manage.py spectacular --file /tmp/supportflow-schema.yml --validate
```

`check --deploy` should be run against production-like settings before deployment.

## Operational Rules

- Do not expose `.env` files.
- Do not log API keys, JWTs, passwords, or uploaded document contents.
- Do not call OpenAI from browser/client code.
- Keep all organization-scoped queries filtered by membership.
- Keep AI prompts and provider calls out of views/templates.
- Serve uploaded files through controlled infrastructure in production.
- Run database backups for PostgreSQL.
- Monitor Celery workers and failed tasks.

## Known Limitations and Future Improvements

- Add rate limiting for authentication, chat, semantic search, and AI actions.
- Add task status polling and visibility for failed background jobs.
- Add malware scanning for uploaded files before processing.
- Add audit logs for membership changes and destructive actions.
- Add object-level audit trails for document/ticket/evaluation changes.
- Add stricter production file storage, for example S3-compatible object storage.
- Add Content Security Policy middleware.
- Add refresh-token rotation and token blacklist if required by deployment policy.
