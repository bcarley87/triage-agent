from __future__ import annotations

import logging

from pydantic import ValidationError

from triage_agent.agent._client import DEFAULT_MODEL, call_claude, extract_json
from triage_agent.agent.models import TriageDecision
from triage_agent.agent.prompts import triage as triage_prompt
from triage_agent.workbook.models import Candidate, Config

logger = logging.getLogger(__name__)


def triage(candidate: Candidate, config: Config) -> TriageDecision:
    """Decide urgency tier and outreach channel for a classified candidate."""
    model = config.triage_model or DEFAULT_MODEL
    prompt = triage_prompt.build_prompt(candidate, config)

    raw = call_claude(prompt, model=model, temperature=config.temperature)
    logger.debug("Triage raw response for %s:\n%s", candidate.candidate_id, raw[:500])

    try:
        data = extract_json(raw)
        decision = TriageDecision(**data)
    except (ValueError, ValidationError) as exc:
        logger.error(
            "Failed to parse triage response for %s: %s\nRaw: %.300s",
            candidate.candidate_id,
            exc,
            raw,
        )
        raise

    return decision
