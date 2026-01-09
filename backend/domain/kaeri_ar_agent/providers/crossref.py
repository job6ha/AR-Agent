from __future__ import annotations

from typing import Any, Dict, Optional

from . import normalize_doi, request_json
from ..config import AgentConfig
from ..schemas import ProviderWork


class CrossrefClient:
    base_url = "https://api.crossref.org/works"

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def get_by_doi(self, doi: str) -> Optional[ProviderWork]:
        normalized = normalize_doi(doi)
        try:
            payload = request_json(
                f"{self.base_url}/{normalized}",
                params=None,
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return None
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            return None
        return self._to_work(message, normalized)

    def search(self, query: str) -> list[ProviderWork]:
        try:
            payload = request_json(
                self.base_url,
                params={"query": query, "rows": 5},
                headers=self._headers(),
                timeout_s=self._config.provider_timeout_s,
                retry_count=self._config.request_retry_count,
                retry_backoff_s=self._config.request_retry_backoff_s,
            )
        except Exception:
            return []
        items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
        works = []
        for item in items:
            if isinstance(item, dict):
                doi = item.get("DOI") or item.get("doi")
                normalized = normalize_doi(doi) if doi else None
                works.append(self._to_work(item, normalized))
        return works

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "kaeri-ar-agent"}
        return headers

    def _to_work(self, message: Dict[str, Any], doi: Optional[str]) -> ProviderWork:
        title = _first(message.get("title"))
        authors = []
        for author in message.get("author", []):
            if not isinstance(author, dict):
                continue
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            combined = " ".join(part for part in [given, family] if part)
            if combined:
                authors.append(combined)
        year = None
        issued = message.get("issued", {}).get("date-parts", [])
        if issued and isinstance(issued, list) and issued[0]:
            year = issued[0][0]
        venue = _first(message.get("container-title"))
        url = message.get("URL")
        status_flags = _status_flags(message)
        return ProviderWork(
            provider="crossref",
            provider_id=message.get("DOI") or message.get("doi"),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            identifiers={"doi": doi} if doi else {},
            status_flags=status_flags,
            raw=message,
        )


def _first(value: Any) -> Optional[str]:
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return None


def _status_flags(message: Dict[str, Any]) -> list[str]:
    flags: list[str] = []
    relations = message.get("relation") or {}
    if isinstance(relations, dict):
        for rel_type, rel_items in relations.items():
            if not isinstance(rel_items, list):
                continue
            lowered = rel_type.lower()
            if "retract" in lowered:
                flags.append("retracted")
            if "correct" in lowered:
                flags.append("corrected")
            if "concern" in lowered:
                flags.append("eoc")
    updates = message.get("update-to") or []
    if isinstance(updates, list):
        for update in updates:
            if not isinstance(update, dict):
                continue
            update_type = str(update.get("type", "")).lower()
            if "retract" in update_type:
                flags.append("retracted")
            if "correct" in update_type:
                flags.append("corrected")
            if "concern" in update_type:
                flags.append("eoc")
    return sorted(set(flags))
