from triage_agent.extractors.extractor import CandidateExtractor


def test_extractor_returns_empty_list() -> None:
    extractor = CandidateExtractor()
    assert extractor.extract({}) == []


def test_extractor_returns_list_type() -> None:
    extractor = CandidateExtractor()
    result = extractor.extract({"patients": [1, 2, 3]})
    assert isinstance(result, list)
