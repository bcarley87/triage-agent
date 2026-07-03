from __future__ import annotations

import logging
import uuid

from triage_agent.agent._client import DEFAULT_MODEL, call_claude
from triage_agent.agent.models import TriageDecision
from triage_agent.agent.prompts import drafter as drafter_prompt
from triage_agent.workbook.models import Candidate, Config, Draft

logger = logging.getLogger(__name__)

SMS_MAX_CHARS = 320


def draft_message(candidate: Candidate, triage_decision: TriageDecision, config: Config) -> Draft:
    """Draft an outreach message for email or sms channels. Returns a Draft with status Pending."""
    if triage_decision.channel not in ("email", "sms"):
        raise ValueError(
            f"draft_message called with unsupported channel '{triage_decision.channel}'. "
            "Only 'email' and 'sms' are valid."
        )

    model = config.triage_model or DEFAULT_MODEL
    prompt = drafter_prompt.build_prompt(candidate, triage_decision, config)

    draft_text = call_claude(
        prompt,
        model=model,
        temperature=config.temperature,
        max_tokens=512 if triage_decision.channel == "sms" else 1024,
    ).strip()

    if triage_decision.channel == "sms" and len(draft_text) > SMS_MAX_CHARS:
        logger.warning(
            "SMS draft for %s is %d chars (over %d). Truncating at word boundary.",
            candidate.candidate_id,
            len(draft_text),
            SMS_MAX_CHARS,
        )
        draft_text = _truncate_sms(draft_text)

    return Draft(
        draft_id=f"draft-{uuid.uuid4().hex[:8]}",
        candidate_id=candidate.candidate_id,
        channel=triage_decision.channel,
        draft_text=draft_text,
        approval_status="Pending",
    )


def _truncate_sms(text: str, limit: int = SMS_MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last_space = truncated.rfind(" ")
    return truncated[:last_space].rstrip() if last_space > 0 else truncated
