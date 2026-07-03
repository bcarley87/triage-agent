"""Unit tests for classifier.py — all Claude calls are mocked."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from triage_agent.agent.classifier import classify
from triage_agent.agent.models import ClassificationResult
from triage_agent.workbook.models import Candidate, Config

VOCAB = {
    "abnormal_lab": "lab value outside the normal range",
    "critical_lab": "lab value in the emergency-notify range",
    "chronic_patient": "patient has one or more chronic conditions",
    "elderly": "patient is 70 or older",
    "missed_appointment": "patient did not attend their scheduled visit",
    "medication_change": "appointment involved adjusting a medication",
    "new_diagnosis": "patient received a new diagnosis at this visit",
    "overdue_monitoring": "scheduled monitoring interval has lapsed",
}


@pytest.fixture()
def config() -> Config:
    return Config(
        classifier_model="claude-sonnet-4-5",
        triage_model="claude-sonnet-4-5",
        temperature=0.3,
        flag_vocabulary=VOCAB,
    )


@pytest.fixture()
def candidate() -> Candidate:
    return Candidate(
        candidate_id="C001",
        patient_id="P001",
        patient_name="Test Patient",
        visit_type="Lab Review",
        lab_type="HbA1c",
        lab_value="10.2%",
        admin_notes="HbA1c above target of 7%.",
    )


def _mock_response(payload: dict) -> str:
    return json.dumps(payload)


def test_classify_returns_classification_result(candidate, config):
    payload = {
        "trigger_reason": "abnormal_hba1c_result",
        "flags": ["abnormal_lab", "chronic_patient"],
        "classification_confidence": 0.92,
        "rationale": "HbA1c of 10.2% is above the 7% target.",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)):
        result = classify(candidate, config)

    assert isinstance(result, ClassificationResult)
    assert result.trigger_reason == "abnormal_hba1c_result"
    assert result.classification_confidence == pytest.approx(0.92)


def test_classify_filters_unknown_flags(candidate, config):
    payload = {
        "trigger_reason": "test",
        "flags": ["abnormal_lab", "invented_flag_xyz"],
        "classification_confidence": 0.8,
        "rationale": "test",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)):
        result = classify(candidate, config)

    assert "invented_flag_xyz" not in result.flags
    assert "abnormal_lab" in result.flags


def test_classify_keeps_known_flags(candidate, config):
    payload = {
        "trigger_reason": "test",
        "flags": ["abnormal_lab", "chronic_patient", "elderly"],
        "classification_confidence": 0.85,
        "rationale": "test",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)):
        result = classify(candidate, config)

    assert set(result.flags) == {"abnormal_lab", "chronic_patient", "elderly"}


def test_classify_handles_json_code_fence(candidate, config):
    raw = "```json\n" + json.dumps({
        "trigger_reason": "abnormal_lab_result",
        "flags": ["abnormal_lab"],
        "classification_confidence": 0.7,
        "rationale": "Test",
    }) + "\n```"

    with patch("triage_agent.agent.classifier.call_claude", return_value=raw):
        result = classify(candidate, config)

    assert result.trigger_reason == "abnormal_lab_result"


def test_classify_raises_on_invalid_json(candidate, config):
    with patch("triage_agent.agent.classifier.call_claude", return_value="not json at all"):
        with pytest.raises((ValueError, Exception)):
            classify(candidate, config)


def test_classify_uses_config_model(candidate, config):
    payload = {
        "trigger_reason": "test",
        "flags": [],
        "classification_confidence": 0.5,
        "rationale": "test",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)) as mock_call:
        classify(candidate, config)

    mock_call.assert_called_once()
    _, kwargs = mock_call.call_args
    assert kwargs.get("model") == "claude-sonnet-4-5"


def test_classify_includes_flag_vocabulary_in_prompt(candidate, config):
    payload = {
        "trigger_reason": "test",
        "flags": [],
        "classification_confidence": 0.5,
        "rationale": "test",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)) as mock_call:
        classify(candidate, config)

    prompt = mock_call.call_args[0][0]
    assert "abnormal_lab" in prompt
    assert "critical_lab" in prompt


def test_classify_includes_candidate_data_in_prompt(candidate, config):
    payload = {
        "trigger_reason": "test",
        "flags": [],
        "classification_confidence": 0.5,
        "rationale": "test",
    }
    with patch("triage_agent.agent.classifier.call_claude", return_value=_mock_response(payload)) as mock_call:
        classify(candidate, config)

    prompt = mock_call.call_args[0][0]
    assert "Test Patient" in prompt
    assert "HbA1c" in prompt
    assert "10.2%" in prompt
