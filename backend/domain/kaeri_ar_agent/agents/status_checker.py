from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..config import AgentConfig
from ..providers import ProviderClients, build_provider_clients, normalize_doi
from ..schemas import SourceRecord, StatusRecord


@dataclass
class StatusCheckResult:
    sources: List[SourceRecord]
    warnings: List[str]
    errors: List[str]


def check_status(
    config: AgentConfig,
    sources: List[SourceRecord],
    providers: Optional[ProviderClients] = None,
) -> StatusCheckResult:
    """Label sources with integrity flags and drop disallowed items."""
    if providers is None:
        providers = build_provider_clients(config)
    warnings: List[str] = []
    errors: List[str] = []
    remaining: List[SourceRecord] = []
    for source in sources:
        doi = _get_doi(source)
        status = StatusRecord(flags=[], status_evidence=[])
        if doi and not config.mock_mode:
            work = providers.crossref.get_by_doi(doi)
            if work:
                status.flags = list(work.status_flags)
                if work.status_flags:
                    status.status_evidence.append("crossref")
        if not status.flags:
            status.flags = ["unknown"]
        updated = source.model_copy(update={"status": status})
        if "retracted" in status.flags:
            message = f"Retracted source excluded: {source.title or source.source_id}"
            if config.verify_mode == "soft":
                warnings.append(message)
            else:
                errors.append(message)
            continue
        if any(flag in status.flags for flag in ["corrected", "eoc"]):
            warnings.append(f"Source has integrity flag ({', '.join(status.flags)}): {source.title or source.source_id}")
        remaining.append(updated)
    return StatusCheckResult(sources=remaining, warnings=warnings, errors=errors)


def _get_doi(source: SourceRecord) -> Optional[str]:
    if source.canonical_metadata and source.canonical_metadata.doi:
        return normalize_doi(source.canonical_metadata.doi)
    if source.identifiers and source.identifiers.doi:
        return normalize_doi(source.identifiers.doi)
    if source.doi:
        return normalize_doi(source.doi)
    return None
