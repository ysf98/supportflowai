# SupportFlow AI Business Rules

This document describes the main product rules implemented in SupportFlow AI.

## Users

- Users authenticate with email and password.
- `email` is the primary login identifier.
- Registration creates an initial organization.
- The registering user becomes owner of that organization.
- A user can belong to multiple organizations.

## Organizations

Organizations represent workspaces.

Every major resource belongs to an organization:

- documents,
- chunks,
- conversations,
- tickets,
- evaluation cases,
- evaluation runs,
- dashboard metrics.

Normal users can only access resources in organizations where they have an active membership.

## Roles

Initial roles:

```txt
owner
admin
agent
viewer
```

Role order:

```txt
viewer < agent < admin < owner
```

## Role Capabilities

### Owner

Can:

- manage the organization,
- manage members,
- upload and process documents,
- generate embeddings,
- use chat,
- manage tickets,
- run evaluations,
- view dashboard metrics.

### Admin

Can:

- manage members,
- upload and process documents,
- generate embeddings,
- use chat,
- manage tickets,
- run evaluations,
- view dashboard metrics.

Cannot:

- transfer owner role through normal membership endpoints.

### Agent

Can:

- use chat,
- create and manage tickets,
- add comments,
- resolve tickets,
- run support workflows.

Cannot:

- upload/process documents unless granted admin-level permissions,
- manage organization members.

### Viewer

Can:

- read accessible resources,
- use chat if member of the organization,
- view dashboard data for accessible organizations.

Cannot:

- upload documents,
- process documents,
- generate embeddings,
- mutate tickets,
- run AI ticket actions,
- manage members.

## Superuser Behavior

Superusers are treated as global admins for administrative visibility.

They can access global dashboard data and organization resources.

## Documents

Supported upload formats:

```txt
.txt
.md
```

Document statuses:

```txt
uploaded
processing
processed
failed
```

Rules:

- files must not be empty,
- filenames must not contain path separators,
- files must pass extension and content type validation,
- files must stay under `SUPPORTFLOW_MAX_UPLOAD_SIZE`,
- stored file paths use generated UUID names,
- original filenames are retained as metadata,
- only processed documents can generate embeddings,
- documents must have chunks before embeddings can be generated.

## Chunks and Embeddings

Chunk embedding statuses:

```txt
pending
processing
ready
failed
```

Rules:

- new chunks start as `pending`,
- successful embedding generation sets `ready`,
- failed generation sets `failed` and stores a safe error,
- semantic search only uses ready chunks,
- semantic search is always organization-scoped.

## Chat RAG

Rules:

- conversations belong to one organization,
- only members can create or access conversations in that organization,
- questions are saved as user messages,
- answers are saved as assistant messages,
- answers must be based on retrieved context,
- answer sources are stored as backend records,
- no context means safe insufficient-information answer,
- cross-organization sources are rejected.

## Tickets

Ticket statuses:

```txt
open
in_progress
waiting
resolved
closed
```

Priorities:

```txt
low
medium
high
urgent
```

Categories:

```txt
billing
technical
account
product
other
```

Rules:

- tickets belong to one organization,
- `created_by` is set by the server,
- assigned users must belong to the same organization,
- agents/admins/owners can manage tickets,
- viewers cannot mutate tickets,
- AI classification updates category, priority, and summary,
- AI suggested replies are stored on the ticket,
- resolving a ticket can optionally create a public comment.

## Evaluations

Evaluation cases define:

- question,
- expected answer,
- optional expected document.

Evaluation runs store:

- generated answer,
- retrieved sources,
- score,
- pass/fail,
- notes.

Rules:

- cases belong to one organization,
- expected documents must belong to the same organization,
- only organization members can create/run evaluations,
- runs execute the RAG flow and score simple quality criteria.

## Dashboard

Dashboard metrics are organization-scoped.

Normal users see metrics for their active memberships only.

Superusers can see global metrics.

## Async Workflows

Celery-backed workflows:

- document processing,
- embedding generation,
- ticket classification,
- ticket reply suggestion,
- evaluation run execution.

Async endpoints return task metadata with `202 Accepted`.

## Security Rules

- No real secrets in code.
- No `.env` committed.
- No external AI calls in tests.
- No organization-scoped query without membership filtering.
- No AI calls from frontend code.
- No internal tracebacks in user-facing AI errors.
- No uploaded file path traversal.

## Out of Scope for Current Version

- soft delete,
- billing/subscriptions,
- public customer portal,
- email notifications,
- PDF parsing,
- advanced audit logs,
- rate limiting,
- production object storage.
