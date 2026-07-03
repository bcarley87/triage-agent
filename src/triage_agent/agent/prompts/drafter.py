"""Prompt template for the outreach message drafter pass."""
from __future__ import annotations

from triage_agent.agent.models import TriageDecision
from triage_agent.workbook.models import Candidate, Config

_CHANNEL_GUIDANCE = {
    "sms": (
        "CHANNEL: SMS\n"
        "• Maximum 320 characters total — count carefully\n"
        "• One or two short sentences only\n"
        "• Be direct and warm; no greetings longer than 2 words\n"
        "• Include [CLINIC_PHONE] for the callback number"
    ),
    "email": (
        "CHANNEL: Email\n"
        "• 2 to 4 short paragraphs\n"
        "• Warm, professional tone\n"
        "• Include a brief greeting and a clear call to action\n"
        "• Include [CLINIC_PHONE] at least once\n"
        "• Close with the clinic name placeholder [CLINIC_NAME]"
    ),
}


def build_prompt(candidate: Candidate, triage_decision: TriageDecision, config: Config) -> str:
    flags_str = ", ".join(candidate.flags) if candidate.flags else "none"
    channel_guidance = _CHANNEL_GUIDANCE.get(triage_decision.channel, "")
    lab_context = (
        f"{candidate.lab_type} results are available"
        if candidate.lab_type
        else "recent visit or appointment record"
    )
    outreach_reason = _outreach_reason(candidate)

    return f"""You are drafting a patient outreach message for an Endocrinology clinic nurse to review \
before it is sent. Write in second person directly to the patient.

━━━ {channel_guidance}

━━━ STRICT CONTENT RULES (violations will cause this draft to be rejected) ━━━
✗ Never state or imply a diagnosis ("You have...", "Your condition is...", "This indicates...")
✗ Never advise medication changes or doses ("You should take...", "Increase your...")
✗ Never interpret or quote specific lab values in the message
✗ Never make clinical judgements or prognoses
✓ Always include [CLINIC_PHONE] as the callback number placeholder
✓ Write as if a nurse composed the message — warm, caring, not alarming
✓ The purpose is to invite the patient to contact the clinic, not to inform them of findings

━━━ CANDIDATE CONTEXT ━━━
  Patient Name    : {candidate.patient_name}
  Reason          : {outreach_reason}
  Clinical flags  : {flags_str}
  Visit context   : {candidate.visit_type or "Recent visit"}
  Lab context     : {lab_context}
  Urgency level   : {triage_decision.urgency_tier}

━━━ WHAT TO COMMUNICATE ━━━
{_what_to_communicate(candidate, triage_decision)}

━━━ OUTPUT ━━━
Return ONLY the message text. No JSON, no labels, no metadata. Just the message to send."""


def _outreach_reason(candidate: Candidate) -> str:
    trigger = candidate.trigger_reason or ""
    if "missed" in trigger or "missed_appointment" in (candidate.flags or []):
        return "missed recent appointment"
    if "critical" in trigger or "critical_lab" in (candidate.flags or []):
        return "urgent lab results requiring attention"
    if "abnormal" in trigger or "abnormal_lab" in (candidate.flags or []):
        return "recent lab results to discuss"
    if "overdue" in trigger or "overdue_monitoring" in (candidate.flags or []):
        return "overdue lab work or monitoring"
    if "medication" in trigger or "medication_change" in (candidate.flags or []):
        return "recent medication adjustment"
    if "new_diagnosis" in (candidate.flags or []):
        return "recent clinic visit and new care plan"
    return "recent visit follow-up"


def _what_to_communicate(candidate: Candidate, decision: TriageDecision) -> str:
    flags = set(candidate.flags or [])
    urgency = decision.urgency_tier

    if "missed_appointment" in flags:
        return (
            "• We noticed you missed your recent appointment and wanted to check in\n"
            "• Kindly ask them to call us at [CLINIC_PHONE] to reschedule\n"
            "• Keep the tone supportive, not accusatory"
        )
    if urgency == "high":
        return (
            "• We have been trying to reach them regarding their recent lab work\n"
            "• Ask them to call [CLINIC_PHONE] as soon as possible\n"
            "• Convey some urgency without being alarming"
        )
    if "overdue_monitoring" in flags:
        return (
            "• It has been a while since their last labs or screening\n"
            "• Invite them to schedule an appointment or lab draw\n"
            "• Provide [CLINIC_PHONE] to call or schedule"
        )
    if "new_diagnosis" in flags:
        return (
            "• Following up after their recent visit\n"
            "• Remind them we are here to support them as they begin their care plan\n"
            "• Encourage them to call [CLINIC_PHONE] with any questions"
        )
    # Default: routine follow-up
    return (
        "• Following up after their recent visit or regarding recent lab results\n"
        "• Invite them to call [CLINIC_PHONE] if they have questions or need to schedule\n"
        "• Keep the message brief and warm"
    )
