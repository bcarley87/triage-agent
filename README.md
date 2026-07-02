# Triage Agent

Automated patient followup triage agent for healthcare clinics. Beachhead specialty: Endocrinology.

Automates three workflows:
- **Post-visit calls** — follow up with patients after appointments
- **Lab result chasing** — notify patients of pending or returned lab results
- **Appointment reminders** — proactive reminders for upcoming visits

## Stack

- **Python 3.12** with FastAPI
- **SQLAlchemy 2.0** (async) + PostgreSQL
- **Anthropic SDK** for Claude-powered triage logic
- **Click** for CLI jobs
- **uv** for dependency management, **Ruff** for linting

## Getting Started

```bash
# Copy env config
cp .env.example .env
# Edit .env with your values

# Start Postgres
docker compose up -d db

# Install dependencies
uv sync

# Run the API
uv run uvicorn triage_agent.api.app:app --reload

# Health check
curl http://localhost:8000/health
```

## CLI

```bash
# Run the nightly candidate extraction job
uv run triage extract-candidates
```

## Testing

```bash
uv run pytest
```

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Project Structure

```
src/triage_agent/
├── api/          # FastAPI app and routes
├── delivery/     # Outreach dispatching (phone, SMS, email)
├── extractors/   # Candidate extraction from source systems
├── shared/       # DB models, settings, session utilities
└── triage/       # Urgency scoring logic
migrations/       # Raw SQL schema migrations (001_, 002_, ...)
tests/            # Mirrors src/triage_agent/ structure
```

## Database Migrations

Migrations in `migrations/` are numbered SQL files (`001_initial_schema.sql`, etc.).
When running via Docker Compose, Postgres executes them automatically on first start via `docker-entrypoint-initdb.d`.
For subsequent runs against an existing volume, apply migrations manually:

```bash
psql postgresql://triage:triage@localhost:5432/triage_agent -f migrations/001_initial_schema.sql
```
