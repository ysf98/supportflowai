# SupportFlow AI Demo Data

SupportFlow AI includes a deterministic development seed command for portfolio demos.

The command creates a complete local dataset that can be used to show the web UI, API, RAG flow, tickets, evaluations, dashboard metrics, and async-ready workflows.

## Command

```bash
docker compose run --rm web python manage.py seed_demo_data
```

Or, inside a running container:

```bash
docker compose exec web python manage.py seed_demo_data
```

## Default Credentials

```txt
Email: demo@example.com
Password: DemoPass123!
Organization: Demo Workspace
```

## Custom Options

```bash
python manage.py seed_demo_data \
  --email demo@example.com \
  --password DemoPass123! \
  --name "Demo User" \
  --organization "Demo Workspace"
```

PowerShell single-line example:

```powershell
docker compose run --rm web python manage.py seed_demo_data --email demo@example.com --password DemoPass123! --name "Demo User" --organization "Demo Workspace"
```

## Created Data

The command creates or reuses:

- demo user,
- demo organization,
- owner membership,
- demo knowledge base document,
- processed document text,
- document chunks,
- fake deterministic embeddings,
- RAG conversation,
- user and assistant messages,
- answer sources,
- support tickets,
- ticket comments,
- AI ticket classifications,
- AI suggested replies,
- evaluation case,
- evaluation run.

## Idempotency

The command is safe to run multiple times in development.

It reuses the main demo resources when they already exist and fills in missing derived data, such as chunks, embeddings, ticket AI fields, conversation messages, and evaluation runs.

## AI Safety

The seed command forces `AI_PROVIDER=fake` while generating embeddings, RAG answers, ticket suggestions, and evaluation runs.

It does not call OpenAI or any external AI provider.

## Recommended Demo Flow

1. Run migrations.
2. Run `seed_demo_data`.
3. Start the stack.
4. Log in with the demo credentials.
5. Open the dashboard.
6. Inspect the demo document and chunks.
7. Open the RAG conversation and sources.
8. Review tickets and AI-generated fields.
9. Open evaluations and inspect the generated run.

## Notes

This command is intended for local development and portfolio demos. Do not run it in production.
