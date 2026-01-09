from backend.domain.kaeri_ar_agent.providers import (
    build_provider_clients,
    normalize_doi,
    request_json,
)
from backend.domain.kaeri_ar_agent.providers.crossref import CrossrefClient
from backend.domain.kaeri_ar_agent.providers.openalex import OpenAlexClient
from backend.domain.kaeri_ar_agent.providers.semanticscholar import SemanticScholarClient
from backend.domain.kaeri_ar_agent.providers.unpaywall import UnpaywallClient
from backend.domain.kaeri_ar_agent.config import AgentConfig


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1234/ABCD") == "10.1234/abcd"


def test_request_json_success(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    def fake_get(*_args, **_kwargs):
        return FakeResponse()

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.httpx.get", fake_get)
    payload = request_json("http://example.com", None, None, 1.0, 0, 0.0)
    assert payload["ok"] is True


def test_request_json_raises_on_failure(monkeypatch):
    def fake_get(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.httpx.get", fake_get)
    try:
        request_json("http://example.com", None, None, 1.0, 0, 0.0)
    except Exception as exc:
        assert "boom" in str(exc)


def test_crossref_get_by_doi(monkeypatch):
    payload = {"message": {"title": ["Title"], "DOI": "10.1/abc", "author": []}}

    def fake_request(*_args, **_kwargs):
        return payload

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.crossref.request_json", fake_request)
    client = CrossrefClient(AgentConfig())
    work = client.get_by_doi("10.1/abc")
    assert work is not None
    assert work.title == "Title"


def test_openalex_search(monkeypatch):
    payload = {"results": [{"title": "Title", "doi": "https://doi.org/10.1/abc", "id": "OA1"}]}

    def fake_request(*_args, **_kwargs):
        return payload

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.openalex.request_json", fake_request)
    client = OpenAlexClient(AgentConfig(openalex_mailto="test@example.com"))
    works = client.search("query")
    assert works[0].doi == "10.1/abc"


def test_semanticscholar_search(monkeypatch):
    payload = {"data": [{"title": "Title", "externalIds": {"DOI": "10.2/xyz"}}]}

    def fake_request(*_args, **_kwargs):
        return payload

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.semanticscholar.request_json", fake_request)
    client = SemanticScholarClient(AgentConfig())
    works = client.search("query")
    assert works[0].doi == "10.2/xyz"


def test_unpaywall_get_by_doi(monkeypatch):
    payload = {"best_oa_location": {"url": "https://oa.example.com"}}

    def fake_request(*_args, **_kwargs):
        return payload

    monkeypatch.setattr("backend.domain.kaeri_ar_agent.providers.unpaywall.request_json", fake_request)
    client = UnpaywallClient(AgentConfig(unpaywall_email="user@example.com"))
    work = client.get_by_doi("10.3/qwe")
    assert work.url == "https://oa.example.com"


def test_build_provider_clients():
    clients = build_provider_clients(AgentConfig())
    assert clients.crossref is not None
    assert clients.openalex is not None
    assert clients.semanticscholar is not None
    assert clients.unpaywall is not None
