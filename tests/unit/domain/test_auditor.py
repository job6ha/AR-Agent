from backend.domain.kaeri_ar_agent.agents.auditor import audit_citations
from backend.domain.kaeri_ar_agent.schemas import DraftNode, SourceRecord


def test_audit_citations_basic():
    source = SourceRecord(source_id="S-1", title="Title")
    draft = DraftNode(
        chapter_id="C1",
        paragraph_id="P1",
        text="text (S-1)",
        citation_source_ids=["S-1"],
    )
    audit = audit_citations([source], [draft], llm=None)
    assert audit.passed is True
