"""Prompt template for the urgency and channel triage pass."""
from __future__ import annotations

from triage_agent.workbook.models import Candidate, Config


def build_prompt(candidate: Candidate, config: Config) -> str:
    flags_str = ", ".join(candidate.flags) if candidate.flags else "none"
    appt_date = candidate.appointment_date.isoformat() if candidate.appointment_date else "N/A"

    return f"""You are a clinical triage decision engine for an Endocrinology specialty clinic. \
A candidate has already been classified with flags. Your job is to assign urgency tier and outreach channel.

━━━ URGENCY RULES (evaluate top-down, stop at first match) ━━━
HIGH urgency if ANY of the following:
  • critical_lab is present
  • missed_appointment AND prior_no_show are both present
  • elderly is present AND any lab flag (abnormal_lab or critical_lab) is present
  • new_diagnosis AND critical_lab are both present

MEDIUM urgency if ANY of the following (and not already HIGH):
  • abnormal_lab is present
  • missed_appointment is present (first time, no prior_no_show)
  • new_diagnosis is present
  • overdue_monitoring is present
  • post_procedure AND elderly are both present
  • overdue_monitoring AND prior_no_show are both present

LOW urgency otherwise:
  • medication_change only
  • post_procedure without elderly flag
  • routine post-visit chronic patient check-in

━━━ CHANNEL RULES ━━━
nurse_callback:
  • Always when urgency is HIGH
  • When critical_lab is present (regardless of urgency)
  • When missed_appointment + prior_no_show (patient unreachable pattern)
  • When escalation is clinically warranted (adrenal flags, cortisol concerns)

email:
  • Default channel for MEDIUM urgency without nurse_callback trigger
  • Appropriate for overdue_monitoring, new_diagnosis, abnormal_lab follow-ups
  • Use when the message benefits from a longer explanation

sms:
  • LOW urgency reminders
  • When a brief, direct nudge is more appropriate than a full email
  • For missed appointment reminders (first time, medium urgency)

no_action:
  • Duplicate entry, data quality issue, or already handled

━━━ ENDOCRINOLOGY ESCALATION GUIDANCE ━━━
• Diabetes: critical glucose or HbA1c ≥ 13% → same-day nurse callback
• Thyroid: TSH < 0.01 or > 15 mIU/L → callback within 24h
• Adrenal: any cortisol flag, adrenal insufficiency concern → always nurse_callback
• Elderly patients (70+): escalate one tier above what the lab alone would suggest

━━━ CANDIDATE ━━━
  Name          : {candidate.patient_name}
  Trigger       : {candidate.trigger_reason or "N/A"}
  Flags         : {flags_str}
  Visit Type    : {candidate.visit_type or "N/A"}
  Appointment   : {appt_date}
  Lab Test      : {candidate.lab_type or "N/A"}
  Lab Value     : {candidate.lab_value or "N/A"}
  Admin Notes   : {candidate.admin_notes or "N/A"}

━━━ OUTPUT ━━━
Return ONLY valid JSON. No prose, no code fences.
Set escalation_reason to a short string if channel is nurse_callback; otherwise null.

{{
  "urgency_tier": "low|medium|high",
  "channel": "email|sms|nurse_callback|no_action",
  "flags_added": [],
  "rationale": "One to two sentences explaining the decision.",
  "escalation_reason": null
}}"""
