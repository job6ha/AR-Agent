from backend.domain.kaeri_ar_agent.agents.resolver import resolve_sources
from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.providers import ProviderClients
from backend.domain.kaeri_ar_agent.schemas import ProviderWork, SourceRecord


class FakeCrossref:
    def __init__(self, work):
        self._work = work

    def get_by_doi(self, doi):
        return self._work

    def search(self, query):
        return []


class FakeOpenAlex:
    def get_by_doi(self, doi):
        return None

    def search(self, query):
        return []

    def get_by_id(self, work_id):
        return None


class FakeS2(FakeOpenAlex):
    pass


class FakeUnpaywall:
    def get_by_doi(self, doi):
        return None


def test_resolver_prefers_doi_crossref():
    work = ProviderWork(
        provider="crossref",
        title="Canonical Title",
        authors=["Kim"],
        year=2024,
        venue="Journal",
        doi="10.1234/abcd",
        url="https://doi.org/10.1234/abcd",
    )
    providers = ProviderClients(
        crossref=FakeCrossref(work),
        openalex=FakeOpenAlex(),
        semanticscholar=FakeS2(),
        unpaywall=FakeUnpaywall(),
    )
    config = AgentConfig(mock_mode=False)
    source = SourceRecord(
        source_id="S-ARXIV-1234.5678",
        title="Original Title",
        doi="10.1234/abcd",
        url="https://arxiv.org/abs/1234.5678",
    )
    resolved, stats = resolve_sources(config, [source], providers=providers)
    assert stats.doi_confirmed == 1
    assert resolved[0].canonical_source_id == "doi:10.1234/abcd"
    assert resolved[0].canonical_metadata.title == "Canonical Title"


def test_resolver_preprint_only_when_no_doi():
    providers = ProviderClients(
        crossref=FakeCrossref(None),
        openalex=FakeOpenAlex(),
        semanticscholar=FakeS2(),
        unpaywall=FakeUnpaywall(),
    )
    config = AgentConfig(mock_mode=False)
    source = SourceRecord(
        source_id="S-ARXIV-9999.0000",
        title="Preprint Only",
        url="https://arxiv.org/abs/9999.0000",
    )
    resolved, stats = resolve_sources(config, [source], providers=providers)
    assert stats.preprint_only == 1
    assert resolved[0].canonical_source_id == "arxiv:9999.0000"
    assert resolved[0].preprint_only is True
