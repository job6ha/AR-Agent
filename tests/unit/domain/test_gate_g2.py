from backend.domain.kaeri_ar_agent.gates import gate_g2_citations
from backend.domain.kaeri_ar_agent.schemas import DraftNode, SourceRecord


def test_gate_g2_accepts_canonical_ids():
    source = SourceRecord(
        source_id="S-ARXIV-0004",
        title="Canonical Paper",
        canonical_source_id="doi:10.9999/abc",
    )
    draft = DraftNode(
        chapter_id="C1",
        paragraph_id="C1-P1",
        text="Sample text (doi:10.9999/abc)",
        citation_source_ids=["doi:10.9999/abc"],
    )
    audit = gate_g2_citations([source], [draft])
    assert audit.passed is True


def test_gate_g2_fails_on_missing_citation():
    source = SourceRecord(
        source_id="S-ARXIV-0005",
        title="Canonical Paper",
        canonical_source_id="doi:10.9999/xyz",
    )
    draft = DraftNode(
        chapter_id="C1",
        paragraph_id="C1-P1",
        text="Sample text (doi:10.9999/missing)",
        citation_source_ids=["doi:10.9999/missing"],
    )
    audit = gate_g2_citations([source], [draft])
    assert audit.passed is False


def test_gate_g1_sources_requires_locator():
    from backend.domain.kaeri_ar_agent.gates import gate_g1_sources

    source = SourceRecord(source_id="S-1", title="Title")
    audit = gate_g1_sources([source])
    assert audit.passed is False
