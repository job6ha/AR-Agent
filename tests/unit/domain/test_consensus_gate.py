from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.gates.g1a_consensus import gate_g1a_consensus
from backend.domain.kaeri_ar_agent.providers import ProviderClients
from backend.domain.kaeri_ar_agent.schemas import ProviderWork, SourceRecord


class FakeProvider:
    def __init__(self, work):
        self._work = work

    def get_by_doi(self, doi):
        return self._work

    def search(self, query):
        return []


def _providers(crossref_work, openalex_work=None, s2_work=None):
    return ProviderClients(
        crossref=FakeProvider(crossref_work),
        openalex=FakeProvider(openalex_work),
        semanticscholar=FakeProvider(s2_work),
        unpaywall=FakeProvider(None),
    )


def test_g1a_consensus_passes_on_matching_metadata():
    work = ProviderWork(
        provider="crossref",
        title="AI reactor safety",
        authors=["S. Kim"],
        year=2023,
        venue="Nuclear Journal",
        doi="10.5555/xyz",
    )
    openalex = ProviderWork(
        provider="openalex",
        title="AI reactor safety",
        authors=["S. Kim"],
        year=2023,
        venue="Nuclear Journal",
        doi="10.5555/xyz",
    )
    providers = _providers(work, openalex_work=openalex)
    config = AgentConfig(mock_mode=False)
    source = SourceRecord(
        source_id="S-ARXIV-0001",
        title="AI reactor safety",
        authors=["S. Kim"],
        year=2023,
        doi="10.5555/xyz",
    )
    result = gate_g1a_consensus(config, [source], providers=providers)
    assert result.audit.passed is True
    assert len(result.sources) == 1
    assert result.sources[0].verification.identity_score >= 0.85


def test_g1a_consensus_rejects_on_mismatch():
    work = ProviderWork(
        provider="crossref",
        title="Unrelated paper",
        authors=["J. Park"],
        year=2018,
        venue="Other Journal",
        doi="10.1111/bad",
    )
    providers = _providers(work)
    config = AgentConfig(mock_mode=False)
    source = SourceRecord(
        source_id="S-ARXIV-0002",
        title="AI reactor safety",
        authors=["S. Kim"],
        year=2023,
        doi="10.1111/bad",
    )
    result = gate_g1a_consensus(config, [source], providers=providers)
    assert result.audit.passed is False
    assert len(result.rejected) == 1
