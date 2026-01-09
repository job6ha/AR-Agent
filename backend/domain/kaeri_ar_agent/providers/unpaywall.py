from __future__ import annotations

from typing import Any, Dict, Optional

from . import normalize_doi, request_json
from ..config import AgentConfig
from ..schemas import ProviderWork


class UnpaywallClient:
    base_url = "https://api.unpaywall.org/v2"

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def get_by_doi(self, doi: str) -> Optional[ProviderWork]:
        normalized = normalize_doi(doi)
        if not self._config.unpaywall_email:
            return None
        try:
            payload = request_json(
                f"{self.base_url}/{normalized}",
                params={"email": self._config.unpaywall_email},
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return self._to_work(payload, normalized)

    def search(self, query: str) -> list[ProviderWork]:
        return []

    def get_by_id(self, work_id: str) -> Optional[ProviderWork]:
        return None

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": "kaeri-ar-agent"}

    def _to_work(self, item: Dict[str, Any], doi: str) -> ProviderWork:
        oa_location = item.get("best_oa_location") or {}
        url = oa_location.get("url") if isinstance(oa_location, dict) else None
        return ProviderWork(
            provider="unpaywall",
            provider_id=doi,
            title=item.get("title"),
            doi=doi,
            url=url,
            identifiers={"doi": doi},
            raw=item,
        )
