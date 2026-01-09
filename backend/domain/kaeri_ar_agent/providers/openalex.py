from __future__ import annotations

from typing import Any, Dict, Optional

from . import normalize_doi, request_json
from ..config import AgentConfig
from ..schemas import ProviderWork


class OpenAlexClient:
    base_url = "https://api.openalex.org/works"

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def search(self, query: str) -> list[ProviderWork]:
        params = {"search": query, "per-page": 5}
        if self._config.openalex_mailto:
            params["mailto"] = self._config.openalex_mailto
        try:
            payload = request_json(
                self.base_url,
                params=params,
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return []
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [self._to_work(item) for item in results if isinstance(item, dict)]

    def get_by_doi(self, doi: str) -> Optional[ProviderWork]:
        normalized = normalize_doi(doi)
        url = f"{self.base_url}/https://doi.org/{normalized}"
        try:
            payload = request_json(
                url,
                params=None,
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

    def get_by_id(self, work_id: str) -> Optional[ProviderWork]:
        try:
            payload = request_json(
                f"{self.base_url}/{work_id}",
                params=None,
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
        return headers

    def _to_work(self, item: Dict[str, Any]) -> ProviderWork:
        title = item.get("title")
        authors = []
        for author in item.get("authorships", []):
            if not isinstance(author, dict):
                continue
            author_info = author.get("author") or {}
            name = author_info.get("display_name")
            if name:
                authors.append(name)
        year = item.get("publication_year")
        venue = None
        host = item.get("host_venue") or {}
        if isinstance(host, dict):
            venue = host.get("display_name")
        doi = item.get("doi")
        if doi:
            doi = normalize_doi(doi)
        url = item.get("id") or item.get("doi")
        identifiers = {}
        if doi:
            identifiers["doi"] = doi
        if item.get("id"):
            identifiers["openalex_id"] = item.get("id")
        return ProviderWork(
            provider="openalex",
            provider_id=item.get("id"),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            identifiers=identifiers,
            raw=item,
        )
