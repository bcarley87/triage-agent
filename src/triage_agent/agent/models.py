from typing import Literal

from pydantic import BaseModel, field_validator

from triage_agent.workbook.models import Config


class ClassificationResult(BaseModel):
    trigger_reason: str
    flags: list[str]
    classification_confidence: float
    rationale: str

    @field_validator("flags", mode="before")
    @classmethod
    def ensure_list(cls, v: object) -> list[str]:
        if v is None:
            return []
        return list(v)  # type: ignore[arg-type]

    def filter_to_vocabulary(self, config: Config) -> "ClassificationResult":
        """Return a copy with flags restricted to the configured vocabulary."""
        known = frozenset(config.flag_vocabulary.keys())
        return self.model_copy(update={"flags": [f for f in self.flags if f in known]})


class TriageDecision(BaseModel):
    urgency_tier: Literal["low", "medium", "high"]
    channel: Literal["email", "sms", "nurse_callback", "no_action"]
    flags_added: list[str] = []
    rationale: str
    escalation_reason: str | None = None
