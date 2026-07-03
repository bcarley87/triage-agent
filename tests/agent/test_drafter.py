"""Unit tests for drafter.py — all Claude calls are mocked."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from triage_agent.agent.drafter import SMS_MAX_CHARS, draft_message
from triage_agent.agent.models import TriageDecision
from triage_agent.workbook.models import Candidate, Config, Draft


@pytest.fixture()
def config() -> Config:
    return Config(triage_model="claude-sonnet-4-5", temperature=0.3)


@pytest.fixture()
def candidate() -> Candidate:
    return Candidate(
        candidate_id="C001",
        patient_id="P001",
        patient_name="Maria Santos",
        visit_type="Diabetes Follow-up",
        admin_notes="3-month visit. Metformin ongoing.",
        flags=["chronic_patient", "medication_change"],
        trigger_reason="medication_titration_checkin",
        status="Triaged",
    )


@pytest.fixture()
def email_decision() -> TriageDecision:
    return TriageDecision(
        urgency_tier="low",
        channel="email",
        flags_added=[],
        rationale="Routine follow-up.",
    )


@pytest.fixture()
def sms_decision() -> TriageDecision:
    return TriageDecision(
        urgency_tier="low",
        channel="sms",
        flags_added=[],
        rationale="Brief reminder.",
    )


def test_draft_message_returns_draft(candidate, email_decision, config):
    with patch("triage_agent.agent.drafter.call_claude", return_value="Hello Maria, please call [CLINIC_PHONE]."):
        draft = draft_message(candidate, email_decision, config)

    assert isinstance(draft, Draft)
    assert draft.candidate_id == "C001"
    assert draft.channel == "email"
    assert draft.approval_status == "Pending"


def test_draft_message_sms_truncates_overlong(candidate, sms_decision, config):
    long_text = "A" * 500
    with patch("triage_agent.agent.drafter.call_claude", return_value=long_text):
        draft = draft_message(candidate, sms_decision, config)

    assert len(draft.draft_text) <= SMS_MAX_CHARS


def test_draft_message_sms_preserves_short(candidate, sms_decision, config):
    short_text = "Hi Maria, please call us at [CLINIC_PHONE]. Thank you!"
    with patch("triage_agent.agent.drafter.call_claude", return_value=short_text):
        draft = draft_message(candidate, sms_decision, config)

    assert draft.draft_text == short_text


def test_draft_message_draft_id_is_unique(candidate, email_decision, config):
    with patch("triage_agent.agent.drafter.call_claude", return_value="Hi, call [CLINIC_PHONE]."):
        draft1 = draft_message(candidate, email_decision, config)
        draft2 = draft_message(candidate, email_decision, config)

    assert draft1.draft_id != draft2.draft_id


def test_draft_message_rejects_nurse_callback(candidate, config):
    bad_decision = TriageDecision(
        urgency_tier="high",
        channel="nurse_callback",
        flags_added=[],
        rationale="test",
    )
    with pytest.raises(ValueError, match="nurse_callback"):
        draft_message(candidate, bad_decision, config)


def test_draft_message_rejects_no_action(candidate, config):
    bad_decision = TriageDecision(
        urgency_tier="low",
        channel="no_action",
        flags_added=[],
        rationale="test",
    )
    with pytest.raises(ValueError):
        draft_message(candidate, bad_decision, config)


def test_draft_prompt_includes_clinic_phone_instruction(candidate, email_decision, config):
    with patch("triage_agent.agent.drafter.call_claude", return_value="Hi [CLINIC_PHONE].") as mock_call:
        draft_message(candidate, email_decision, config)

    prompt = mock_call.call_args[0][0]
    assert "[CLINIC_PHONE]" in prompt


def test_draft_prompt_includes_channel_constraints(candidate, sms_decision, config):
    with patch("triage_agent.agent.drafter.call_claude", return_value="Hi [CLINIC_PHONE].") as mock_call:
        draft_message(candidate, sms_decision, config)

    prompt = mock_call.call_args[0][0]
    assert "320" in prompt  # SMS char limit mentioned in prompt


def test_draft_prompt_mentions_no_diagnosis_rule(candidate, email_decision, config):
    with patch("triage_agent.agent.drafter.call_claude", return_value="Hi [CLINIC_PHONE].") as mock_call:
        draft_message(candidate, email_decision, config)

    prompt = mock_call.call_args[0][0]
    assert "diagnos" in prompt.lower()
