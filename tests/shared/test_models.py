from triage_agent.shared.models import Base, FollowupCandidate, NurseAction, OutreachLog, Patient


def test_table_names() -> None:
    assert Patient.__tablename__ == "patients"
    assert FollowupCandidate.__tablename__ == "followup_candidates"
    assert OutreachLog.__tablename__ == "outreach_log"
    assert NurseAction.__tablename__ == "nurse_actions"


def test_all_models_share_same_metadata() -> None:
    tables = Base.metadata.tables
    assert "patients" in tables
    assert "followup_candidates" in tables
    assert "outreach_log" in tables
    assert "nurse_actions" in tables


def test_followup_candidate_default_status() -> None:
    col = FollowupCandidate.__table__.c["status"]
    assert col.default.arg == "pending"
