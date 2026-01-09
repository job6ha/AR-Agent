from backend.domain.kaeri_ar_agent.pipeline import (
    _classify_g2_route,
    _classify_qa_route,
    _normalize_citations_node,
)
from backend.domain.kaeri_ar_agent.schemas import DraftNode


def test_classify_g2_route():
    assert _classify_g2_route(["non-standard format"]) == "normalize"
    assert _classify_g2_route(["other issue"]) == "refine"


def test_classify_qa_route():
    assert _classify_qa_route(["주제 일관성"]) == "outline"
    assert _classify_qa_route(["구조 문제"]) == "compose"
    assert _classify_qa_route(["문체 문제"]) == "write"
    assert _classify_qa_route(["출처 문제"]) == "refine"


def test_normalize_citations_node():
    draft = DraftNode(
        chapter_id="C1",
        paragraph_id="P1",
        text="text (S-ARXIV-1234.5678v1)",
        citation_source_ids=["S-ARXIV-1234.5678v1"],
    )
    state = {"drafts": [draft]}
    updated = _normalize_citations_node(state)
    assert "arXiv:1234.5678v1" in updated["drafts"][0].text
