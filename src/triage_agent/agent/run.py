"""Main agent pipeline. Runs classify → triage → draft in a single loop against the workbook."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

import click

from triage_agent.agent.classifier import classify
from triage_agent.agent.drafter import draft_message
from triage_agent.agent.models import TriageDecision
from triage_agent.agent.triage import triage
from triage_agent.workbook.models import Candidate, LogEntry, ManualQueueEntry
from triage_agent.workbook.reader import get_all_candidates, get_config, load_workbook
from triage_agent.workbook.writer import (
    append_draft,
    append_log,
    append_manual_queue,
    save_workbook,
    update_candidate,
)

logger = logging.getLogger(__name__)

Step = Literal["classify", "triage", "draft"]


def run(
    workbook_path: str,
    dry_run: bool = False,
    step: Step | None = None,
) -> None:
    """Run the agent pipeline against the workbook.

    - dry_run: Claude calls execute, but nothing is written to disk.
    - step: restrict to a single pass ("classify", "triage", or "draft").
             When None, all three passes run in sequence.

    Every pass is idempotent: it only processes rows in the expected input status,
    so a crashed run can be safely restarted.
    """
    wb = load_workbook(workbook_path)
    config = get_config(wb)
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    do_classify = step is None or step == "classify"
    do_triage = step is None or step == "triage"
    do_draft = step is None or step == "draft"

    # In-memory staging lets dry_run chain passes without touching the file.
    staged: dict[str, dict] = {}

    def _effective(candidate: Candidate, field: str):
        return staged.get(candidate.candidate_id, {}).get(field, getattr(candidate, field))

    def _stage(candidate_id: str, updates: dict) -> None:
        staged.setdefault(candidate_id, {}).update(updates)

    def _apply_staged(candidate: Candidate) -> Candidate:
        updates = staged.get(candidate.candidate_id)
        if not updates:
            return candidate
        return candidate.model_copy(update=updates)

    def _log(action: str, candidate_id: str, detail: str) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            run_id=run_id,
            action=action,
            candidate_id=candidate_id,
            detail=detail,
        )
        if not dry_run:
            append_log(wb, entry)

    # ── Pass 1: Classify ──────────────────────────────────────────────────────
    if do_classify:
        all_candidates = get_all_candidates(wb)
        new_candidates = [c for c in all_candidates if _effective(c, "status") == "New"]
        click.echo(f"[{run_id}] classify: {len(new_candidates)} New candidates")

        for candidate in new_candidates:
            try:
                result = classify(candidate, config)
            except Exception as exc:
                logger.error("classify failed for %s: %s", candidate.candidate_id, exc)
                _log("classify_error", candidate.candidate_id, str(exc))
                continue

            updates = {
                "trigger_reason": result.trigger_reason,
                "flags": result.flags,
                "status": "Flagged",
            }
            detail = (
                f"trigger={result.trigger_reason} "
                f"flags={','.join(result.flags)} "
                f"confidence={result.classification_confidence:.2f}"
            )

            if dry_run:
                _stage(candidate.candidate_id, updates)
                click.echo(f"  [DRY RUN] classify {candidate.candidate_id}: {detail}")
            else:
                update_candidate(wb, candidate.candidate_id, updates)
                _log("classify", candidate.candidate_id, detail)
                click.echo(f"  classify {candidate.candidate_id}: {detail}")

    # ── Pass 2: Triage ────────────────────────────────────────────────────────
    if do_triage:
        all_candidates = get_all_candidates(wb)
        flagged = [
            _apply_staged(c)
            for c in all_candidates
            if _effective(c, "status") == "Flagged"
        ]
        click.echo(f"[{run_id}] triage: {len(flagged)} Flagged candidates")

        for candidate in flagged:
            try:
                decision = triage(candidate, config)
            except Exception as exc:
                logger.error("triage failed for %s: %s", candidate.candidate_id, exc)
                _log("triage_error", candidate.candidate_id, str(exc))
                continue

            new_status = "Escalated" if decision.channel == "nurse_callback" else "Triaged"
            updates = {
                "urgency_tier": decision.urgency_tier,
                "channel": decision.channel,
                "status": new_status,
            }
            detail = (
                f"urgency={decision.urgency_tier} channel={decision.channel} "
                f"escalation={decision.escalation_reason or 'none'}"
            )

            if dry_run:
                _stage(candidate.candidate_id, updates)
                click.echo(f"  [DRY RUN] triage {candidate.candidate_id}: {detail}")
            else:
                update_candidate(wb, candidate.candidate_id, updates)
                if decision.channel == "nurse_callback":
                    append_manual_queue(
                        wb,
                        ManualQueueEntry(
                            candidate_id=candidate.candidate_id,
                            patient_name=candidate.patient_name,
                            urgency=decision.urgency_tier,
                            summary=decision.rationale,
                            recommended_action=decision.escalation_reason or "Nurse callback required",
                            flags=", ".join(candidate.flags),
                        ),
                    )
                _log("triage", candidate.candidate_id, detail)
                click.echo(f"  triage {candidate.candidate_id}: {detail}")

    # ── Pass 3: Draft ─────────────────────────────────────────────────────────
    if do_draft:
        all_candidates = get_all_candidates(wb)
        to_draft = [
            _apply_staged(c)
            for c in all_candidates
            if _effective(c, "status") == "Triaged"
            and _effective(c, "channel") in ("email", "sms")
        ]
        click.echo(f"[{run_id}] draft: {len(to_draft)} Triaged candidates")

        for candidate in to_draft:
            decision = TriageDecision(
                urgency_tier=_effective(candidate, "urgency_tier") or "low",
                channel=_effective(candidate, "channel"),
                flags_added=[],
                rationale="",
            )
            try:
                draft = draft_message(candidate, decision, config)
            except Exception as exc:
                logger.error("draft failed for %s: %s", candidate.candidate_id, exc)
                _log("draft_error", candidate.candidate_id, str(exc))
                continue

            detail = f"channel={draft.channel} len={len(draft.draft_text)}"

            if dry_run:
                _stage(candidate.candidate_id, {"status": "Draft Ready"})
                click.echo(f"  [DRY RUN] draft {candidate.candidate_id}: {detail}")
                click.echo(f"    preview: {draft.draft_text[:120]}...")
            else:
                append_draft(wb, draft)
                update_candidate(wb, candidate.candidate_id, {"status": "Draft Ready"})
                _log("draft", candidate.candidate_id, detail)
                click.echo(f"  draft {candidate.candidate_id}: {detail}")

    # ── Persist ───────────────────────────────────────────────────────────────
    if not dry_run:
        save_workbook(wb, workbook_path)
        click.echo(f"[{run_id}] saved {workbook_path}")
    else:
        click.echo(f"[{run_id}] dry-run complete — no changes written")
