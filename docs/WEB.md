# SupportFlow AI Web Interface

The web interface is implemented with Django Templates and Bootstrap 5.

The visual layer is designed as a professional internal SaaS interface with:

- dark product sidebar,
- responsive content shell,
- metric cards,
- structured tables,
- status badges,
- empty states,
- styled forms,
- dedicated detail/action panels.

## Entry Points

```txt
/login/
/register/
/
/organizations/
/documents/
/chat/
/tickets/
/evaluations/
/profile/
```

## Current Capabilities

- Register and create an initial workspace.
- Sign in and out with Django session authentication.
- View dashboard metrics.
- Create organizations.
- Upload `.txt` and `.md` documents, then queue processing and embedding jobs.
- Ask RAG questions and view cited sources.
- Create, comment, and resolve tickets; queue AI classification and suggested replies.
- Create evaluation cases and queue RAG evaluation runs.
- View user profile and memberships.

## Notes

The web interface reuses the same domain services as the API. It does not duplicate RAG, ticket AI, embeddings, or evaluation logic in templates or views.

Long-running actions use Celery tasks where appropriate. After queueing a job, refresh the relevant detail page to see updated results once the worker finishes.

The UI is intentionally server-rendered for the first professional demo. A richer frontend can be added later if needed.
