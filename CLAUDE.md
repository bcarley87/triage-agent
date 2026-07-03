# Triage Agent — CLAUDE.md

## Project Overview

Automated patient followup triage agent for healthcare clinics. Beachhead specialty: Endocrinology.

## Architecture

Source of truth is a single Excel workbook (`master.xlsx`). The agent reads and writes to this file.
An admin manually fills in patient and appointment data. The agent adds flags, triages, drafts, and sends.

```
src/triage_agent/
├── workbook/     # All read/write operations against master.xlsx (openpyxl)
│   ├── schema.py     # Column lists, tab names, error types
│   ├── models.py     # Pydantic models: Candidate, Draft, ManualQueueEntry, LogEntry, Config
│   ├── reader.py     # load_workbook, get_candidates_by_status, get_drafts_by_approval, get_config
│   └── writer.py     # update_candidate, append_draft, append_manual_queue, append_log, save_workbook
├── api/          # FastAPI app (Phase 0 scaffold — not active, reserved for later)
├── delivery/     # Outreach dispatching — one class per channel (phone, SMS, email)
├── extractors/   # Candidate extraction — one extractor per source system
├── shared/       # DB engine, session, ORM models, settings (reserved for Phase 2)
└── triage/       # Urgency scoring — stateless, takes a Candidate, returns float
src/testdata/
└── seed_workbook.py  # Generates master.xlsx with 50 Endocrinology sample rows
```

**Writer safety rules (enforced in writer.py — never bypass):**
- Never write to admin-filled columns. Raises `AdminColumnWriteError` if attempted.
- Always create a timestamped backup in `backups/` before overwriting the master file.
- Check for Excel's `~$filename` lock marker before saving. Raises `FileLockError` if present.
- Validate header row against expected schema before any write. Raises `HeaderMismatchError` on mismatch.

## Running Locally

```bash
uv sync                            # install deps
uv run triage seed                 # generate master.xlsx
uv run triage inspect              # summarise workbook state
uv run triage extract-candidates   # nightly extraction job (placeholder)
```

## Testing

```bash
uv run pytest               # all tests
uv run pytest tests/api/    # single module
```

Tests must not require a live database or a real Excel file on disk. Use `tmp_path` fixtures.
The `create_seed_workbook(tmp_path / "master.xlsx")` helper is the standard way to get a test workbook.

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

---

### workbook_change

Use this routine whenever you need to evolve the workbook schema — adding columns, renaming tabs, or changing the Config key-value vocabulary.

**The workbook schema lives in four places. All four must stay in sync:**

| Layer | File | What to change |
|-------|------|----------------|
| Column definitions | `src/triage_agent/workbook/schema.py` | Add/rename column in the right list |
| Pydantic models | `src/triage_agent/workbook/models.py` | Add/rename field, set default if optional |
| Reader | `src/triage_agent/workbook/reader.py` | Handle new field in `_coerce_candidate` or equivalent |
| Seed script | `src/testdata/seed_workbook.py` | Add column to `_CANDIDATE_ROWS` tuples and `_build_candidates_tab` |

**Step-by-step process:**

**1. Add the column to `schema.py`:**
```python
# In the correct list (CANDIDATES_ADMIN_COLUMNS or CANDIDATES_AGENT_COLUMNS)
# Column order in the list = physical column order in the workbook. Never reorder existing columns.
CANDIDATES_AGENT_COLUMNS: list[str] = [
    ...
    "new_column_name",   # ← append here
]
```

**2. Add the field to the Pydantic model in `models.py`:**
```python
class Candidate(BaseModel):
    ...
    new_column_name: str | None = None  # always optional for backward compat
```

**3. Update `reader.py` if the field needs coercion:**
```python
def _coerce_candidate(row: dict) -> dict:
    ...
    # e.g., parse a pipe-separated string into a list
    if isinstance(row.get("new_column_name"), str):
        row["new_column_name"] = row["new_column_name"].split("|")
    ...
```

**4. Update `seed_workbook.py` — two places:**
- Add the new value to the `_CANDIDATE_ROWS` tuples (one value per row)
- Add the column to `ws.append([...])` inside `_build_candidates_tab`

**5. Write a migration for existing files:**

Create `migrations/workbook/NNN_add_<column_name>.py`:
```python
"""Add <column_name> column to Candidates tab."""
import openpyxl
from triage_agent.workbook.schema import TAB_CANDIDATES

def migrate(path: str) -> None:
    wb = openpyxl.load_workbook(path)
    ws = wb[TAB_CANDIDATES]
    # Find insertion point by header position
    headers = [c.value for c in ws[1]]
    insert_at = len(headers) + 1  # append at end
    ws.cell(row=1, column=insert_at).value = "new_column_name"
    wb.save(path)
```

Run with: `uv run python migrations/workbook/NNN_add_<column_name>.py master.xlsx`

**6. Update tests:**
- Add an assertion for the new field in `test_round_trip_*` tests
- Add a test for any new safety rule the column introduces

**7. Verify nothing broke:**
```bash
uv run pytest tests/workbook/
uv run triage seed --force      # regenerate seed
uv run triage inspect           # sanity check
```

**Rules:**
- Never reorder or delete existing columns — that breaks any existing workbook files.
- Never add a required (non-optional) field to the Pydantic model — existing rows won't have it.
- If renaming a column, treat it as delete + add (two migrations, or one combined).
- Config key-value changes only require updating `seed_workbook.py` and `reader.py` (`_parse_config`).

---

### run_eval

Use this routine to run the AI eval harness and interpret results.

**Running the harness:**

```bash
# All three layers
uv run triage eval

# Single layer
uv run triage eval --layer classify
uv run triage eval --layer triage
uv run triage eval --layer draft
```

**Output format:**

Each layer prints a bar chart and a failure list:
```
CLASSIFY EVAL — 18/20 passed
████████████████████░░  90%

FAILURES:
  clf-014  PCOS: expected medication_change — got: new_diagnosis
  clf-019  missed Graves: required prior_no_show not in flags
```

Timestamped JSON is saved to `evals/YYYYMMDD_HHMMSS_<layer>.json`. Each file contains:
- `layer`: which eval ran
- `passed`, `total`, `score`: aggregate counts
- `cases`: list of `{id, description, passed, result, expected, failure_reason}`

**Interpreting scores:**

| Score | Meaning |
|-------|---------|
| 100% | Prompts are well-calibrated for the fixture set |
| 85–99% | Acceptable; review failures to distinguish edge cases from prompt bugs |
| <85% | Prompt needs iteration — use the `iterate_prompt` routine |

A failure is not always a prompt bug — check whether the fixture expectation itself is too strict (e.g., `trigger_reason_contains` substring that's too specific). Fix the fixture before fixing the prompt if the model's answer is semantically correct.

**Re-running after a prompt change:**

```bash
uv run triage eval --layer classify
# Compare pass count vs. prior run in evals/
diff <(jq '.cases[] | select(.passed==false) | .id' evals/<old>.json) \
     <(jq '.cases[] | select(.passed==false) | .id' evals/<new>.json)
```

---

### iterate_prompt

Use this routine to improve a prompt when eval scores are below target or a failure pattern is identified.

**The loop:**

**1. Establish a baseline:**
```bash
uv run triage eval --layer <layer>
# Note: N/20 passed, save the evals/ filename
```

**2. Identify the failure pattern:**

Open the saved JSON and look at `failure_reason` across all failing cases. Group by pattern:
- Missing flag (classifier underflagging)
- Wrong urgency tier (triage misjudging severity)
- Hallucinated flag not in vocabulary (classifier overflagging)
- Draft too long or contains forbidden content

**3. Edit the prompt:**

Prompts live in `src/triage_agent/agent/prompts/`:
- `classifier.py` → `build_prompt()` — flag vocabulary, FLAG APPLICATION RULES, examples
- `triage.py` → `build_prompt()` — URGENCY RULES, CHANNEL RULES, escalation guidance
- `drafter.py` → `build_prompt()` — channel constraints, STRICT CONTENT RULES

**Common fixes:**
- Add an explicit rule for the failing case to the relevant rules section
- Add a concrete example that mirrors the failure
- Tighten a threshold (e.g., "HbA1c > 13% = critical_lab")
- Broaden a rule that's too narrow

**4. Re-run the eval:**
```bash
uv run triage eval --layer <layer>
# Compare new N/20 vs. baseline
```

**5. Accept or revert:**
- If score improved and no previously-passing cases regressed → keep
- If regressions appeared → revert with `git diff src/triage_agent/agent/prompts/` and try a narrower edit
- Commit the prompt change with the score delta in the commit message: `improve classifier prompt: 17→19/20`

**Rules:**
- Always run the full layer eval, not just the failing cases — regressions matter.
- Never special-case a single patient name or value in a prompt — generalise to a rule.
- Do not edit the fixture JSON to make a test pass unless the expectation is genuinely wrong.
- Keep `temperature = 0.0` in `EVAL_CONFIG` so results are deterministic across runs.
