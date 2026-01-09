from backend.domain.kaeri_ar_agent.agents.composer import compose_text
from backend.domain.kaeri_ar_agent.schemas import DraftNode


def test_composer_uses_canonical_metadata_and_preprint_label():
    drafts = [
        DraftNode(
            chapter_id="C1",
            paragraph_id="C1-P1",
            text="내용 (doi:10.0000/preprint)",
            citation_source_ids=["doi:10.0000/preprint"],
        )
    ]
    sources = [
        {
            "source_id": "S-ARXIV-0006",
            "canonical_source_id": "doi:10.0000/preprint",
            "preprint_only": True,
            "canonical_metadata": {
                "title": "Preprint Study",
                "authors": ["A. Lee"],
                "year": 2022,
                "venue": "arXiv",
                "doi": "10.0000/preprint",
                "url": "https://doi.org/10.0000/preprint",
            },
        }
    ]
    text = compose_text(drafts, sources)
    assert "[preprint]" in text
    assert "Preprint Study" in text


def test_composer_replaces_source_ids_with_indices():
    drafts = [
        DraftNode(
            chapter_id="C1",
            paragraph_id="C1-P1",
            text="내용 (S-1)",
            citation_source_ids=["S-1"],
        )
    ]
    sources = [{"source_id": "S-1", "title": "Title"}]
    text = compose_text(drafts, sources)
    assert "[1]" in text
