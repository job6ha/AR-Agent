from backend.domain.kaeri_ar_agent.tools import arxiv_client


def test_parse_arxiv_feed():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/1234.5678v1</id>
        <title>Sample Paper</title>
        <summary>Abstract text</summary>
        <published>2024-01-01T00:00:00Z</published>
        <author><name>Kim</name></author>
      </entry>
    </feed>"""
    results = arxiv_client.parse_arxiv_feed(xml)
    assert results[0]["source_id"] == "S-ARXIV-1234.5678v1"
    assert results[0]["title"] == "Sample Paper"
    assert results[0]["year"] == 2024


def test_query_arxiv_success(monkeypatch):
    class FakeResponse:
        text = "<feed></feed>"

        def raise_for_status(self):
            return None

    def fake_get(*_args, **_kwargs):
        return FakeResponse()

    monkeypatch.setattr(arxiv_client.httpx, "get", fake_get)
    text = arxiv_client.query_arxiv("http://example.com", "query", 1, 1.0)
    assert "<feed>" in text


def test_query_arxiv_retries(monkeypatch):
    calls = {"count": 0}

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(arxiv_client.httpx, "get", fake_get)
    try:
        arxiv_client.query_arxiv("http://example.com", "query", 1, 0.1, retry_count=1, retry_backoff_s=0)
    except RuntimeError:
        pass
    else:
        assert False
    assert calls["count"] == 2


def test_query_arxiv_async_success(monkeypatch):
    class FakeResponse:
        text = "<feed></feed>"

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(arxiv_client.httpx, "AsyncClient", lambda **_kwargs: FakeClient())
    text = asyncio_run(arxiv_client.query_arxiv_async("http://example.com", "q", 1, 1.0))
    assert "<feed>" in text


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
