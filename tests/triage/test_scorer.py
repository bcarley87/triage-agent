from triage_agent.triage.scorer import UrgencyScorer


def test_scorer_returns_float() -> None:
    scorer = UrgencyScorer()
    result = scorer.score({"trigger_reason": "lab_result_pending"})
    assert isinstance(result, float)


def test_scorer_default_score_is_zero() -> None:
    scorer = UrgencyScorer()
    assert scorer.score({}) == 0.0
