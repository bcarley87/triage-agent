"""Prompt template for the candidate classifier pass."""
from __future__ import annotations

from triage_agent.workbook.models import Candidate, Config


def build_prompt(candidate: Candidate, config: Config) -> str:
    flag_section = "\n".join(
        f"  {name}: {defn}" for name, defn in config.flag_vocabulary.items()
    )

    appt_date = candidate.appointment_date.isoformat() if candidate.appointment_date else "N/A"

    return f"""You are a clinical triage classifier for an Endocrinology specialty clinic. Your task is to \
examine an admin-entered patient record and determine:
1. The trigger_reason — a short snake_case string describing why this candidate needs followup
2. Which flags from the approved vocabulary apply to this candidate
3. Your confidence in the classification (0.0 to 1.0)
4. A brief rationale (1–2 sentences)

━━━ APPROVED FLAG VOCABULARY ━━━
You MUST only use flags from this list. Do not invent flags.
{flag_section}

━━━ FLAG APPLICATION RULES ━━━
- critical_lab: only when a lab value is in a clearly dangerous/emergency range
  (e.g., HbA1c ≥ 13%, fasting glucose ≥ 400 mg/dL, cortisol < 1.0 mcg/dL AM)
- abnormal_lab: when a lab value is outside normal range but not in emergency range
- elderly: only when admin_notes explicitly mention patient age ≥ 70
- chronic_patient: apply whenever the patient has diabetes, thyroid disease, adrenal disorder,
  PCOS, acromegaly, osteoporosis, or any ongoing endocrine condition
- prior_no_show: only when admin_notes indicate a prior missed appointment or "second miss"
- post_procedure: when the visit type includes "post-RAI", "post-surgical", "post-procedure",
  or similar procedure-recovery context
- medication_change: when a medication was started, stopped, or dose-adjusted at this visit
- missed_appointment: when the visit type contains "Missed" or admin notes indicate no-show
- overdue_monitoring: when admin_notes indicate labs or screenings are overdue by more than
  the standard interval (e.g., HbA1c overdue by months, annual exam not done)
- new_diagnosis: when admin_notes or visit type indicate a new condition was diagnosed

━━━ CANDIDATE RECORD ━━━
  Patient Name   : {candidate.patient_name}
  Appointment    : {appt_date}
  Visit Type     : {candidate.visit_type or "N/A"}
  Lab Test       : {candidate.lab_type or "N/A"}
  Lab Value      : {candidate.lab_value or "N/A"}
  Admin Notes    : {candidate.admin_notes or "N/A"}

━━━ TRIGGER REASON EXAMPLES ━━━
abnormal_hba1c_result, critical_glucose_result, missed_appointment_followup,
post_visit_checkin, post_procedure_followup, medication_titration_checkin,
overdue_lab_monitoring, new_diagnosis_followup, overdue_annual_screening,
hypothyroid_lab_review, adrenal_lab_review, suppressed_tsh_review

━━━ OUTPUT ━━━
Return ONLY valid JSON. No prose, no code fences, no explanation.

{{
  "trigger_reason": "short_snake_case_string",
  "flags": ["flag_from_vocabulary"],
  "classification_confidence": 0.0,
  "rationale": "One to two sentences explaining the classification."
}}"""
