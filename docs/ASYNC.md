# SupportFlow AI Async Processing

SupportFlow AI uses Celery with Redis for background jobs.

The design keeps domain logic in synchronous services and wraps those services with Celery tasks. This makes the code easier to test, keeps API/web views thin, and allows the same business behavior to run either immediately or in the background.

## Components

- Redis: Celery broker and result backend.
- Celery worker: executes queued jobs.
- Domain services: hold the business logic.
- Celery tasks: load database records by ID, call services, and return compact metadata.

## Tasks

Documents:

```txt
apps.documents.tasks.process_document_task
```

Embeddings:

```txt
apps.embeddings.tasks.generate_document_embeddings_task
apps.embeddings.tasks.generate_organization_pending_embeddings_task
```

Tickets:

```txt
apps.tickets.tasks.classify_ticket_task
apps.tickets.tasks.suggest_ticket_reply_task
```

Evaluations:

```txt
apps.evaluations.tasks.run_evaluation_case_task
```

## API Endpoints

Documents:

```txt
POST /api/documents/{id}/process-async/
POST /api/documents/{id}/generate-embeddings-async/
```

Tickets:

```txt
POST /api/tickets/{id}/classify-async/
POST /api/tickets/{id}/suggest-reply-async/
```

Evaluations:

```txt
POST /api/evaluation-cases/{id}/run-async/
```

Async endpoints return `202 Accepted`:

```json
{
  "task_id": "celery-task-id",
  "status": "queued",
  "resource_type": "document",
  "resource_id": 1,
  "detail": "Document processing has been queued."
}
```

## Web Behavior

The web interface queues background work for:

- document processing,
- embedding generation,
- ticket classification,
- ticket suggested replies,
- evaluation runs.

Users can refresh the relevant page to see updated statuses/results after the worker completes the job.

## Testing

Tests run with:

```txt
CELERY_TASK_ALWAYS_EAGER=True
CELERY_TASK_EAGER_PROPAGATES=True
```

This executes tasks in-process during tests, so the test suite does not need a real worker. AI-related tasks still use `FakeAIProvider` in tests and never call external providers.

## Operational Notes

Check the running worker with:

```bash
docker compose exec worker celery -A config inspect ping
```

Start the full local stack, including the worker:

```bash
docker compose up --build
```

Future improvements can add task status polling endpoints, retries for transient AI provider failures, and a web task activity panel.
