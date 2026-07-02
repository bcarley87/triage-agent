# Triage Agent — CLAUDE.md

## Project Overview

Automated patient followup triage agent for healthcare clinics. Beachhead specialty: Endocrinology.

## Architecture

```
src/triage_agent/
├── api/          # FastAPI app, route handlers, request/response schemas
├── delivery/     # Outreach dispatching — one class per channel (phone, SMS, email)
├── extractors/   # Candidate extraction — one extractor per source system
├── shared/       # DB engine, session, ORM models, settings
└── triage/       # Urgency scoring — stateless, takes a candidate dict, returns float
```

Modules are intentionally thin. Each module contains the logic for one concern.
Shared state lives in `shared/`. No module imports from another module (only from `shared/`).

## Running Locally

```bash
docker compose up -d db       # start Postgres
uv sync                        # install deps
uv run uvicorn triage_agent.api.app:app --reload
uv run triage extract-candidates   # CLI job
```

## Testing

```bash
uv run pytest               # all tests
uv run pytest tests/api/    # single module
```

Tests must not require a live database. Use mocks or in-memory fixtures.

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

---

## Routines

### scaffold_module

Use this routine whenever adding a new module to the project.

**1. Create the module directory under `src/triage_agent/`:**

```
src/triage_agent/<module_name>/
├── __init__.py
└── <primary_class>.py
```

`<module_name>` is `lowercase_underscores`. Examples: `lab_results`, `sms_delivery`.

**2. `__init__.py` — re-export the public class:**

```python
from .<primary_class> import <PrimaryClass>

__all__ = ["<PrimaryClass>"]
```

**3. `<primary_class>.py` — implementation skeleton:**

```python
class <PrimaryClass>:
    """One-line description of what this class does."""

    def <main_method>(self, ...) -> ...:
        raise NotImplementedError
```

Class naming: `PascalCase` that names the role — `LabResultExtractor`, `SmsDispatcher`, `A1cScorer`.

**4. Create the mirrored test directory:**

```
tests/<module_name>/
├── __init__.py
└── test_<primary_class>.py
```

**5. `test_<primary_class>.py` — test skeleton:**

```python
from triage_agent.<module_name>.<primary_class> import <PrimaryClass>


def test_<primary_class>_<what_it_does>() -> None:
    instance = <PrimaryClass>()
    # assert something concrete
```

Test naming: `test_<what_it_does>` — e.g., `test_extractor_returns_empty_list`.
All new modules need at least one passing test before the PR is mergeable.

**6. Wire up any CLI commands in `src/triage_agent/cli.py`:**

```python
@cli.command()
def <command_name>() -> None:
    """Short description shown in --help."""
    ...
```

**7. If the module adds new dependencies:**

```bash
uv add <package>        # runtime dep
uv add --dev <package>  # dev/test only
```

**Checklist before opening a PR for a new module:**
- [ ] `src/triage_agent/<module_name>/` created with `__init__.py` and implementation file
- [ ] `tests/<module_name>/` created with `__init__.py` and test file
- [ ] At least one passing test (`uv run pytest tests/<module_name>/`)
- [ ] Ruff clean (`uv run ruff check src/triage_agent/<module_name>/`)
- [ ] CLI command added if applicable
- [ ] New deps added via `uv add` (not by hand-editing pyproject.toml)
