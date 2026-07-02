from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class Candidate(BaseModel):
    # Admin-filled — agent never writes these
    candidate_id: str
    patient_id: str
    patient_name: str
    appointment_date: date | None = None
    visit_type: str | None = None
    lab_type: str | None = None
    lab_value: str | None = None
    admin_notes: str | None = None

    # Agent-filled — admin may override but usually doesn't
    trigger_reason: str | None = None
    flags: list[str] = []
    urgency_tier: Literal["low", "medium", "high"] | None = None
    channel: Literal["email", "sms", "nurse_callback", "no_action"] | None = None
    status: Literal["New", "Flagged", "Triaged", "Draft Ready", "Escalated", "Approved", "Sent", "Dismissed"] = "New"
    last_updated: datetime | None = None
    specialty_id: str | None = None

    @field_validator("flags", mode="before")
    @classmethod
    def parse_flags(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [f.strip() for f in v.split(",") if f.strip()]
        if v is None:
            return []
        return list(v)  # type: ignore[arg-type]

    @field_validator("appointment_date", mode="before")
    @classmethod
    def parse_date(cls, v: object) -> date | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v  # type: ignore[return-value]


class Draft(BaseModel):
    draft_id: str
    candidate_id: str
    channel: str
    draft_text: str
    approval_status: Literal["Pending", "Approved", "Edited", "Rejected"] = "Pending"
    final_text: str | None = None
    sent_timestamp: datetime | None = None
    response_received: datetime | None = None
    response_text: str | None = None


class ManualQueueEntry(BaseModel):
    candidate_id: str
    patient_name: str
    urgency: str
    summary: str
    recommended_action: str
    flags: str = ""
    assigned_to: str | None = None
    resolved: Literal["Yes", "No"] = "No"
    resolved_notes: str | None = None


class LogEntry(BaseModel):
    timestamp: datetime
    run_id: str
    action: str
    candidate_id: str
    detail: str


class Config(BaseModel):
    autosend_enabled: bool = False
    specialty_scope: list[str] = []
    classifier_model: str = "claude-sonnet-4-6"
    triage_model: str = "claude-sonnet-4-6"
    temperature: float = 0.0
    flag_vocabulary: dict[str, str] = {}
    raw: dict[str, str] = {}
