from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from ..config import AgentConfig


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderClients:
    crossref: Any
    openalex: Any
    semanticscholar: Any
    unpaywall: Any


def normalize_doi(doi: str) -> str:
    return doi.strip().lower().replace("https://doi.org/", "").replace("http://doi.org/", "")


def build_provider_clients(config: AgentConfig) -> ProviderClients:
    from .crossref import CrossrefClient
    from .openalex import OpenAlexClient
    from .semanticscholar import SemanticScholarClient
    from .unpaywall import UnpaywallClient

    return ProviderClients(
        crossref=CrossrefClient(config),
        openalex=OpenAlexClient(config),
        semanticscholar=SemanticScholarClient(config),
        unpaywall=UnpaywallClient(config),
    )


def request_json(
    url: str,
    params: Optional[Dict[str, Any]],
    headers: Optional[Dict[str, str]],
    timeout_s: float,
    retry_count: int,
    retry_backoff_s: float,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(retry_count + 1):
        try:
            response = httpx.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout_s,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                import time

                time.sleep(retry_backoff_s * (attempt + 1))
    if last_error:
        raise ProviderError(str(last_error))
    return {}
