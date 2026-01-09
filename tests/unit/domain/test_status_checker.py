from backend.domain.kaeri_ar_agent.agents.status_checker import check_status
from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.providers import ProviderClients
from backend.domain.kaeri_ar_agent.schemas import ProviderWork, SourceRecord


class FakeCrossref:
    def __init__(self, work):
        self._work = work

    def get_by_doi(self, doi):
        return self._work


class FakeProvider:
    def get_by_doi(self, doi):
        return None


def test_status_checker_excludes_retracted_sources():
    work = ProviderWork(
        provider="crossref",
        title="Retracted Study",
        doi="10.0000/retracted",
        status_flags=["retracted"],
    )
    providers = ProviderClients(
        crossref=FakeCrossref(work),
        openalex=FakeProvider(),
        semanticscholar=FakeProvider(),
        unpaywall=FakeProvider(),
    )
    config = AgentConfig(mock_mode=False, verify_mode="soft")
    source = SourceRecord(
        source_id="S-ARXIV-0003",
        title="Retracted Study",
        doi="10.0000/retracted",
    )
    result = check_status(config, [source], providers=providers)
    assert result.sources == []
    assert any("Retracted source excluded" in warning for warning in result.warnings)
