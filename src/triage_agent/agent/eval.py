"""Eval harness for classifier, triage, and drafter passes.

Reads hand-crafted fixture cases from tests/fixtures/eval_set/<layer>/cases.json,
runs each case through the corresponding agent function, checks expected properties,
and writes a timestamped result to evals/.

Usage:
    uv run triage eval                  # all three layers
    uv run triage eval --layer classify # single layer
    uv run triage eval --layer triage
    uv run triage eval --layer draft
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from triage_agent.agent.classifier import classify
from triage_agent.agent.drafter import draft_message
from triage_agent.agent.models import ClassificationResult, TriageDecision
from triage_agent.agent.triage import triage
from triage_agent.workbook.models import Candidate, Config

logger = logging.getLogger(__name__)

EVAL_SET_DIR = Path("tests/fixtures/eval_set")
EVALS_DIR = Path("evals")

EVAL_CONFIG = Config(
    autosend_enabled=False,
    specialty_scope=["endo"],
    classifier_model="claude-sonnet-4-5",
    triage_model="claude-sonnet-4-5",
    temperature=0.3,
    flag_vocabulary={
        "abnormal_lab": "lab value outside the normal range for this test type",
        "critical_lab": "lab value in the emergency-notify range",
        "chronic_patient": "patient has one or more chronic conditions",
        "elderly": "patient is 70 or older",
        "prior_no_show": "patient has missed at least one appointment in the past year",
        "medication_change": "appointment involved starting, stopping, or adjusting a medication",
        "missed_appointment": "patient did not attend their scheduled visit",
        "overdue_monitoring": "scheduled monitoring interval has lapsed",
        "post_procedure": "appointment was a procedure requiring followup",
        "new_diagnosis": "patient received a new diagnosis at this visit",
    },
)


# ── Classifier eval ───────────────────────────────────────────────────────────

def run_classifier_eval(config: Config = EVAL_CONFIG) -> dict[str, Any]:
    cases = _load_cases("classifier")
    results = []

    for case in cases:
        candidate = Candidate(**case["input"])
        expected = case["expected"]
        try:
            result = classify(candidate, config)
            passed, failures = _check_classifier(result, expected)
            output = result.model_dump()
        except Exception as exc:
            passed, failures, output = False, [f"Exception: {exc}"], None
            logger.error("classifier eval case %s failed: %s", case["id"], exc)

        results.append({"id": case["id"], "description": case["description"],
                        "passed": passed, "failures": failures, "output": output})

    return _build_result("classifier", results, config.classifier_model)


def _check_classifier(result: ClassificationResult, expected: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    for flag in expected.get("required_flags", []):
        if flag not in result.flags:
            failures.append(f"missing required flag: {flag!r}")

    if kw := expected.get("trigger_reason_contains"):
        if kw not in result.trigger_reason:
            failures.append(f"trigger_reason {result.trigger_reason!r} doesn't contain {kw!r}")

    min_conf = expected.get("min_confidence", 0.0)
    if result.classification_confidence < min_conf:
        failures.append(f"confidence {result.classification_confidence:.2f} < min {min_conf}")

    return len(failures) == 0, failures


# ── Triage eval ───────────────────────────────────────────────────────────────

def run_triage_eval(config: Config = EVAL_CONFIG) -> dict[str, Any]:
    cases = _load_cases("triage")
    results = []

    for case in cases:
        candidate = Candidate(**case["input"])
        expected = case["expected"]
        try:
            decision = triage(candidate, config)
            passed, failures = _check_triage(decision, expected)
            output = decision.model_dump()
        except Exception as exc:
            passed, failures, output = False, [f"Exception: {exc}"], None
            logger.error("triage eval case %s failed: %s", case["id"], exc)

        results.append({"id": case["id"], "description": case["description"],
                        "passed": passed, "failures": failures, "output": output})

    return _build_result("triage", results, config.triage_model)


def _check_triage(decision: TriageDecision, expected: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if "urgency_tier" in expected and decision.urgency_tier != expected["urgency_tier"]:
        failures.append(
            f"urgency_tier {decision.urgency_tier!r} != expected {expected['urgency_tier']!r}"
        )

    allowed = expected.get("allowed_channels")
    if allowed is not None and decision.channel not in allowed:
        failures.append(f"channel {decision.channel!r} not in allowed {allowed}")

    if "channel" in expected and decision.channel != expected["channel"]:
        failures.append(f"channel {decision.channel!r} != expected {expected['channel']!r}")

    return len(failures) == 0, failures


# ── Drafter eval ──────────────────────────────────────────────────────────────

def run_drafter_eval(config: Config = EVAL_CONFIG) -> dict[str, Any]:
    cases = _load_cases("drafter")
    results = []

    for case in cases:
        candidate = Candidate(**case["input"]["candidate"])
        decision = TriageDecision(**case["input"]["triage_decision"])
        expected = case["expected"]
        try:
            draft = draft_message(candidate, decision, config)
            passed, failures = _check_draft(draft.draft_text, draft.approval_status, expected)
            output = draft.model_dump()
        except Exception as exc:
            passed, failures, output = False, [f"Exception: {exc}"], None
            logger.error("drafter eval case %s failed: %s", case["id"], exc)

        results.append({"id": case["id"], "description": case["description"],
                        "passed": passed, "failures": failures, "output": output})

    return _build_result("drafter", results, config.triage_model)


def _check_draft(text: str, approval_status: str, expected: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if approval_status != "Pending":
        failures.append(f"approval_status {approval_status!r} != 'Pending'")

    max_len = expected.get("max_length")
    if max_len is not None and len(text) > max_len:
        failures.append(f"length {len(text)} > max {max_len}")

    min_len = expected.get("min_length", 20)
    if len(text) < min_len:
        failures.append(f"length {len(text)} < min {min_len}")

    placeholder = expected.get("has_placeholder", "[CLINIC_PHONE]")
    if placeholder and placeholder not in text:
        failures.append(f"missing placeholder {placeholder!r}")

    for phrase in expected.get("must_not_contain", []):
        if phrase.lower() in text.lower():
            failures.append(f"text contains forbidden phrase {phrase!r}")

    return len(failures) == 0, failures


# ── Shared helpers ────────────────────────────────────────────────────────────

def _load_cases(layer: str) -> list[dict]:
    path = EVAL_SET_DIR / layer / "cases.json"
    if not path.exists():
        raise FileNotFoundError(f"Eval cases not found: {path}")
    return json.loads(path.read_text())


def _build_result(layer: str, case_results: list[dict], model: str) -> dict[str, Any]:
    passed = sum(1 for r in case_results if r["passed"])
    total = len(case_results)
    score = passed / total if total > 0 else 0.0
    return {
        "timestamp": datetime.now().isoformat(),
        "layer": layer,
        "model": model,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "score": round(score, 4),
        "cases": case_results,
    }


def save_result(result: dict[str, Any]) -> Path:
    EVALS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EVALS_DIR / f"{ts}_{result['layer']}.json"
    path.write_text(json.dumps(result, indent=2))
    return path


def print_summary(result: dict[str, Any]) -> None:
    layer = result["layer"]
    score = result["score"]
    passed = result["passed"]
    total = result["total"]
    model = result["model"]
    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"\n{'─'*55}")
    print(f"  Layer : {layer}  |  Model: {model}")
    print(f"  Score : {bar}  {passed}/{total}  ({score:.0%})")
    failures = [(r["id"], r["failures"]) for r in result["cases"] if not r["passed"]]
    if failures:
        print(f"  Failures ({len(failures)}):")
        for case_id, msgs in failures[:5]:
            for msg in msgs:
                print(f"    [{case_id}] {msg}")
        if len(failures) > 5:
            print(f"    ... and {len(failures)-5} more")
    print(f"{'─'*55}")
