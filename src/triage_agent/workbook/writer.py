import logging
import shutil
from datetime import datetime
from pathlib import Path

from triage_agent.workbook.models import Draft, LogEntry, ManualQueueEntry
from triage_agent.workbook.reader import WorkbookContext, get_sheet_headers, validate_sheet_headers
from triage_agent.workbook.schema import (
    CANDIDATES_ADMIN_SET,
    CANDIDATES_ALL_COLUMNS,
    DRAFTS_COLUMNS,
    LOG_COLUMNS,
    MANUAL_QUEUE_COLUMNS,
    TAB_CANDIDATES,
    TAB_DRAFTS,
    TAB_LOG,
    TAB_MANUAL_QUEUE,
    AdminColumnWriteError,
    CandidateNotFoundError,
    FileLockError,
)

logger = logging.getLogger(__name__)

_BACKUPS_DIR = "backups"


def update_candidate(wb_ctx: WorkbookContext, candidate_id: str, updates: dict) -> None:
    """Write agent-filled columns for a candidate row. Raises on any admin column attempt."""
    illegal = frozenset(updates.keys()) & CANDIDATES_ADMIN_SET
    if illegal:
        msg = f"Attempted write to admin-only column(s): {sorted(illegal)}"
        logger.error(msg)
        raise AdminColumnWriteError(msg)

    ws = wb_ctx.wb[TAB_CANDIDATES]
    validate_sheet_headers(ws, CANDIDATES_ALL_COLUMNS)

    headers = get_sheet_headers(ws)
    col_idx = {name: i + 1 for i, name in enumerate(headers)}

    id_col = col_idx["candidate_id"]
    for row in ws.iter_rows(min_row=2):
        if row[id_col - 1].value == candidate_id:
            for col_name, value in updates.items():
                cell_value = ", ".join(value) if isinstance(value, list) else value
                ws.cell(row=row[0].row, column=col_idx[col_name]).value = cell_value
            ws.cell(row=row[0].row, column=col_idx["last_updated"]).value = datetime.now().isoformat()
            return

    raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in Candidates tab")


def append_draft(wb_ctx: WorkbookContext, draft: Draft) -> None:
    ws = wb_ctx.wb[TAB_DRAFTS]
    validate_sheet_headers(ws, DRAFTS_COLUMNS)
    ws.append([
        draft.draft_id,
        draft.candidate_id,
        draft.channel,
        draft.draft_text,
        draft.approval_status,
        draft.final_text,
        draft.sent_timestamp.isoformat() if draft.sent_timestamp else None,
        draft.response_received.isoformat() if draft.response_received else None,
        draft.response_text,
    ])


def append_manual_queue(wb_ctx: WorkbookContext, entry: ManualQueueEntry) -> None:
    ws = wb_ctx.wb[TAB_MANUAL_QUEUE]
    validate_sheet_headers(ws, MANUAL_QUEUE_COLUMNS)
    ws.append([
        entry.candidate_id,
        entry.patient_name,
        entry.urgency,
        entry.summary,
        entry.recommended_action,
        entry.flags,
        entry.assigned_to,
        entry.resolved,
        entry.resolved_notes,
    ])


def append_log(wb_ctx: WorkbookContext, entry: LogEntry) -> None:
    ws = wb_ctx.wb[TAB_LOG]
    validate_sheet_headers(ws, LOG_COLUMNS)
    ws.append([
        entry.timestamp.isoformat(),
        entry.run_id,
        entry.action,
        entry.candidate_id,
        entry.detail,
    ])


def save_workbook(wb_ctx: WorkbookContext, path: str | Path) -> None:
    """Save with a timestamped backup. Raises FileLockError if file is open elsewhere."""
    path = Path(path)
    _check_file_lock(path)

    if path.exists():
        backups_dir = path.parent / _BACKUPS_DIR
        backups_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups_dir / f"{path.stem}_{stamp}{path.suffix}"
        shutil.copy2(path, backup_path)
        logger.info("Backup created: %s", backup_path)

    wb_ctx.wb.save(path)
    logger.info("Saved workbook: %s", path)


def _check_file_lock(path: Path) -> None:
    """Check for Excel's ~$filename lock marker and OS-level write lock."""
    lock_marker = path.parent / f"~${path.name}"
    if lock_marker.exists():
        raise FileLockError(
            f"'{path.name}' appears to be open in another application. "
            f"Close it and try again. (Lock marker: {lock_marker})"
        )
    if path.exists():
        try:
            with open(path, "r+b"):
                pass
        except (OSError, PermissionError) as exc:
            raise FileLockError(f"Cannot open '{path}' for writing: {exc}") from exc
