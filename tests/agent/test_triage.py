"""Unit tests for triage.py — all Claude calls are mocked."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from triage_agent.agent.models import TriageDecision
from triage_agent.agent.triage import triage
from triage_agent.workbook.models import Candidate, Config


@pytest.fixture()
def config() -> Config:
    return Config(
        triage_model="claude-sonnet-4-5",
        temperature=0.3,
    )


@pytest.fixture()
def flagged_candidate() -> Candidate:
    return Candidate(
        candidate_id="C013",
        patient_id="P013",
        patient_name="Jennifer White",
        visit_type="Lab Review",
        lab_type="HbA1c",
        lab_value="10.2%",
        admin_notes="HbA1c above target.",
        flags=["abnormal_lab", "chronic_patient"],
        trigger_reason="abnormal_hba1c_result",
        status="Flagged",
    )


def _mock(payload: dict) -> str:
    return json.dumps(payload)


def test_triage_returns_triage_decision(flagged_candidate, config):
    payload = {
        "urgency_tier": "medium",
        "channel": "email",
        "flags_added": [],
        "rationale": "Elevated HbA1c, no critical flags.",
        "escalation_reason": None,
    }
    with patch("triage_agent.agent.triage.call_claude", return_value=_mock(payload)):
        decision = triage(flagged_candidate, config)

    assert isinstance(decision, TriageDecision)
    assert decision.urgency_tier == "medium"
    assert decision.channel == "email"


def test_triage_critical_lab_returns_nurse_callback(config):
    candidate = Candidate(
        candidate_id="C023",
        patient_id="P023",
        patient_name="Eleanor Harris",
        flags=["critical_lab", "elderly", "chronic_patient"],
        trigger_reason="critical_lab_result",
        status="Flagged",
    )
    payload = {
        "urgency_tier": "high",
        "channel": "nurse_callback",
        "flags_added": [],
        "rationale": "Critical lab in elderly patient.",
        "escalation_reason": "Critical HbA1c requires same-day nurse callback.",
    }
    with patch("triage_agent.agent.triage.call_claude", return_value=_mock(payload)):
        decision = triage(candidate, config)

    assert decision.urgency_tier == "high"
    assert decision.channel == "nurse_callback"
    assert decision.escalation_reason is not None


def test_triage_handles_json_code_fence(flagged_candidate, config):
    raw = "```json\n" + json.dumps({
        "urgency_tier": "medium",
        "channel": "email",
        "flags_added": [],
        "rationale": "test",
        "escalation_reason": None,
    }) + "\n```"
    with patch("triage_agent.agent.triage.call_claude", return_value=raw):
        decision = triage(flagged_candidate, config)
    assert decision.urgency_tier == "medium"


def test_triage_raises_on_invalid_json(flagged_candidate, config):
    with patch("triage_agent.agent.triage.call_claude", return_value="not json"):
        with pytest.raises((ValueError, Exception)):
            triage(flagged_candidate, config)


def test_triage_passes_flags_to_prompt(flagged_candidate, config):
    payload = {
        "urgency_tier": "medium",
        "channel": "email",
        "flags_added": [],
        "rationale": "test",
        "escalation_reason": None,
    }
    with patch("triage_agent.agent.triage.call_claude", return_value=_mock(payload)) as mock_call:
        triage(flagged_candidate, config)

    prompt = mock_call.call_args[0][0]
    assert "abnormal_lab" in prompt
    assert "chronic_patient" in prompt


def test_triage_uses_config_model(flagged_candidate, config):
    payload = {
        "urgency_tier": "low",
        "channel": "email",
        "flags_added": [],
        "rationale": "test",
        "escalation_reason": None,
    }
    with patch("triage_agent.agent.triage.call_claude", return_value=_mock(payload)) as mock_call:
        triage(flagged_candidate, config)

    _, kwargs = mock_call.call_args
    assert kwargs.get("model") == "claude-sonnet-4-5"


def test_triage_escalation_reason_optional(flagged_candidate, config):
    payload = {
        "urgency_tier": "medium",
        "channel": "email",
        "flags_added": [],
        "rationale": "Routine abnormal lab.",
        "escalation_reason": None,
    }
    with patch("triage_agent.agent.triage.call_claude", return_value=_mock(payload)):
        decision = triage(flagged_candidate, config)

    assert decision.escalation_reason is None
