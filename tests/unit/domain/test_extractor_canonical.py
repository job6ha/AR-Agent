from backend.domain.kaeri_ar_agent.agents.extractor import extract_evidence
from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.schemas import SourceRecord


def test_extractor_uses_canonical_source_id():
    config = AgentConfig(mock_mode=True)
    source = SourceRecord(
        source_id="S-ARXIV-0007",
        title="Sample Paper",
        canonical_source_id="doi:10.2222/test",
    )
    evidence = extract_evidence(config, [source], ["C1"])
    assert evidence[0].source_id == "doi:10.2222/test"


def test_extractor_skips_empty_abstract():
    config = AgentConfig(mock_mode=False)
    source = SourceRecord(
        source_id="S-1",
        title="Title",
        abstract=None,
    )
    evidence = extract_evidence(config, [source], ["C1"], llm=None)
    assert evidence == []
