from backend.domain.kaeri_ar_agent.agents.writer import write_chapters
from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.schemas import EvidenceItem


def test_writer_uses_evidence_source_ids():
    config = AgentConfig(mock_mode=True)
    evidence = [
        EvidenceItem(
            claim_id="C1-001",
            source_id="doi:10.1234/test",
            snippet="snippet",
            chapter_id="C1",
        )
    ]
    drafts = write_chapters(config, "topic", None, [], ["C1"], evidence)
    assert "doi:10.1234/test" in drafts[0].text
    assert drafts[0].citation_source_ids == ["doi:10.1234/test"]
