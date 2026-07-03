from __future__ import annotations

import logging

from pydantic import ValidationError

from triage_agent.agent._client import DEFAULT_MODEL, call_claude, extract_json
from triage_agent.agent.models import ClassificationResult
from triage_agent.agent.prompts import classifier as classifier_prompt
from triage_agent.workbook.models import Candidate, Config

logger = logging.getLogger(__name__)


def classify(candidate: Candidate, config: Config) -> ClassificationResult:
    """Classify a candidate row using Claude. Returns trigger_reason and flags."""
    model = config.classifier_model or DEFAULT_MODEL
    prompt = classifier_prompt.build_prompt(candidate, config)

    raw = call_claude(prompt, model=model, temperature=config.temperature)
    logger.debug("Classifier raw response for %s:\n%s", candidate.candidate_id, raw[:500])

    try:
        data = extract_json(raw)
        result = ClassificationResult(**data)
    except (ValueError, ValidationError) as exc:
        logger.error(
            "Failed to parse classifier response for %s: %s\nRaw: %.300s",
            candidate.candidate_id,
            exc,
            raw,
        )
        raise

    result = result.filter_to_vocabulary(config)

    if not result.flags:
        logger.warning("Classifier returned no known flags for %s", candidate.candidate_id)

    return result
