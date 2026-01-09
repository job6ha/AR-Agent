from backend.domain.kaeri_ar_agent.schemas import (
    CanonicalMetadata,
    EvidenceLinks,
    SourceRecord,
)


def test_source_record_primary_and_locator():
    source = SourceRecord(
        source_id="S-1",
        title="Test",
        source_type="paper",
    )
    assert source.is_primary() is True
    assert source.has_resolvable_locator() is False

    source = source.model_copy(update={"doi": "10.1234/abcd"})
    assert source.has_resolvable_locator() is True


def test_source_record_uses_canonical_metadata_locator():
    source = SourceRecord(
        source_id="S-2",
        title="Test",
        canonical_metadata=CanonicalMetadata(doi="10.1111/xyz"),
    )
    assert source.has_resolvable_locator() is True


def test_source_record_uses_evidence_links_locator():
    source = SourceRecord(
        source_id="S-3",
        title="Test",
        evidence_links=EvidenceLinks(landing_page_url="https://example.com"),
    )
    assert source.has_resolvable_locator() is True
