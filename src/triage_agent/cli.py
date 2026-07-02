from __future__ import annotations

from collections import Counter
from pathlib import Path

import click


@click.group()
def cli() -> None:
    """Triage Agent CLI."""


@cli.command()
def extract_candidates() -> None:
    """Run the nightly followup candidate extraction job."""
    click.echo("candidate job placeholder")


@cli.command()
@click.option("--output", default="master.xlsx", show_default=True, help="Output path for the workbook.")
@click.option("--force", is_flag=True, help="Overwrite existing file.")
def seed(output: str, force: bool) -> None:
    """Generate a seed master.xlsx with 50 sample Endocrinology candidates."""
    from testdata.seed_workbook import _CANDIDATE_ROWS, create_seed_workbook

    path = Path(output)
    if path.exists() and not force:
        click.echo(f"{path} already exists. Use --force to overwrite.", err=True)
        raise SystemExit(1)

    create_seed_workbook(path)
    click.echo(f"Created {path} with {len(_CANDIDATE_ROWS)} seed candidates.")


@cli.command()
@click.option("--file", "workbook_path", default="master.xlsx", show_default=True, help="Path to master workbook.")
def inspect(workbook_path: str) -> None:
    """Print a summary of the master workbook: status counts, pending drafts, unresolved queue."""
    from triage_agent.workbook.reader import get_all_candidates, get_config, get_drafts_by_approval, load_workbook
    from triage_agent.workbook.schema import TAB_MANUAL_QUEUE

    path = Path(workbook_path)
    if not path.exists():
        click.echo(f"Error: {path} not found. Run 'triage seed' to create it.", err=True)
        raise SystemExit(1)

    wb = load_workbook(path)

    candidates = get_all_candidates(wb)
    status_counts: Counter[str] = Counter(c.status for c in candidates)
    pending_drafts = get_drafts_by_approval(wb, "Pending")

    # Read Manual Queue directly to count unresolved rows
    ws_queue = wb.wb[TAB_MANUAL_QUEUE]
    queue_rows = list(ws_queue.iter_rows(min_row=2, values_only=True))
    unresolved = sum(1 for r in queue_rows if r and r[7] != "Yes")  # column 8 = resolved

    config = get_config(wb)

    click.echo(f"\n=== Triage Agent Workbook Summary ===")
    click.echo(f"File      : {path}")
    click.echo(f"Specialty : {', '.join(config.specialty_scope) or '(none)'}")
    click.echo(f"Autosend  : {'ON' if config.autosend_enabled else 'OFF'}")
    click.echo(f"\nCandidates ({len(candidates)} total):")

    statuses = ["New", "Flagged", "Triaged", "Draft Ready", "Escalated", "Approved", "Sent", "Dismissed"]
    for s in statuses:
        count = status_counts.get(s, 0)
        bar = "#" * count if count <= 20 else "#" * 20 + f"+{count - 20}"
        click.echo(f"  {s:<14}: {count:>4}  {bar}")

    click.echo(f"\nDrafts pending approval : {len(pending_drafts)}")
    click.echo(f"Manual queue unresolved : {unresolved}")
    click.echo()
