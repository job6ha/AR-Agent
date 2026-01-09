from __future__ import annotations

from typing import Any, Dict, Optional

from . import normalize_doi, request_json
from ..config import AgentConfig
from ..schemas import ProviderWork


class SemanticScholarClient:
    base_url = "https://api.semanticscholar.org/graph/v1/paper"

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def search(self, query: str) -> list[ProviderWork]:
        params = {
            "query": query,
            "limit": 5,
            "fields": "title,authors,year,venue,externalIds,url",
        }
        try:
            payload = request_json(
                f"{self.base_url}/search",
                params=params,
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return []
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return [self._to_work(item) for item in data if isinstance(item, dict)]

    def get_by_doi(self, doi: str) -> Optional[ProviderWork]:
        normalized = normalize_doi(doi)
        try:
            payload = request_json(
                f"{self.base_url}/DOI:{normalized}",
                params={"fields": "title,authors,year,venue,externalIds,url"},
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return self._to_work(payload)

    def get_by_id(self, paper_id: str) -> Optional[ProviderWork]:
        try:
            payload = request_json(
                f"{self.base_url}/{paper_id}",
                params={"fields": "title,authors,year,venue,externalIds,url"},
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return self._to_work(payload)

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "kaeri-ar-agent"}
        if self._config.semanticscholar_api_key:
            headers["x-api-key"] = self._config.semanticscholar_api_key
        return headers

    def _to_work(self, item: Dict[str, Any]) -> ProviderWork:
        title = item.get("title")
        authors = []
        for author in item.get("authors", []):
            if not isinstance(author, dict):
                continue
            name = author.get("name")
            if name:
                authors.append(name)
        year = item.get("year")
        venue = item.get("venue")
        identifiers = {}
        external = item.get("externalIds") or {}
        doi = external.get("DOI") if isinstance(external, dict) else None
        if doi:
            doi = normalize_doi(doi)
            identifiers["doi"] = doi
        if item.get("paperId"):
            identifiers["s2_paper_id"] = item.get("paperId")
        url = item.get("url")
        return ProviderWork(
            provider="semanticscholar",
            provider_id=item.get("paperId"),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            identifiers=identifiers,
            raw=item,
        )
