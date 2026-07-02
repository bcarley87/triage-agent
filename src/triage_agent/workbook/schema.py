"""Column definitions, tab names, and exceptions for the master workbook."""

TAB_CANDIDATES = "Candidates"
TAB_DRAFTS = "Drafts"
TAB_MANUAL_QUEUE = "Manual Queue"
TAB_LOG = "Log"
TAB_CONFIG = "Config"

# Order matters: must match the physical column order in the workbook.
CANDIDATES_ADMIN_COLUMNS: list[str] = [
    "candidate_id",
    "patient_id",
    "patient_name",
    "appointment_date",
    "visit_type",
    "lab_type",
    "lab_value",
    "admin_notes",
]

CANDIDATES_AGENT_COLUMNS: list[str] = [
    "trigger_reason",
    "flags",
    "urgency_tier",
    "channel",
    "status",
    "last_updated",
    "specialty_id",
]

CANDIDATES_ALL_COLUMNS: list[str] = CANDIDATES_ADMIN_COLUMNS + CANDIDATES_AGENT_COLUMNS
CANDIDATES_ADMIN_SET: frozenset[str] = frozenset(CANDIDATES_ADMIN_COLUMNS)
CANDIDATES_AGENT_SET: frozenset[str] = frozenset(CANDIDATES_AGENT_COLUMNS)

DRAFTS_COLUMNS: list[str] = [
    "draft_id",
    "candidate_id",
    "channel",
    "draft_text",
    "approval_status",
    "final_text",
    "sent_timestamp",
    "response_received",
    "response_text",
]

MANUAL_QUEUE_COLUMNS: list[str] = [
    "candidate_id",
    "patient_name",
    "urgency",
    "summary",
    "recommended_action",
    "flags",
    "assigned_to",
    "resolved",
    "resolved_notes",
]

LOG_COLUMNS: list[str] = [
    "timestamp",
    "run_id",
    "action",
    "candidate_id",
    "detail",
]

CONFIG_COLUMNS: list[str] = ["key", "value"]


class WorkbookError(Exception):
    """Base class for workbook errors."""


class AdminColumnWriteError(WorkbookError):
    """Raised when a write is attempted to an admin-only column."""


class HeaderMismatchError(WorkbookError):
    """Raised when the workbook header row does not match the expected schema."""


class FileLockError(WorkbookError):
    """Raised when the workbook file appears to be open in another application."""


class CandidateNotFoundError(WorkbookError):
    """Raised when a candidate_id is not found in the Candidates tab."""
