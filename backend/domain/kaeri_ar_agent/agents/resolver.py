from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional

from ..config import AgentConfig
from ..providers import ProviderClients, build_provider_clients, normalize_doi
from ..schemas import (
    CanonicalMetadata,
    EvidenceLinks,
    IdentifierRecord,
    ProviderWork,
    SourceRecord,
)


DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


@dataclass
class ResolveStats:
    total: int = 0
    doi_confirmed: int = 0
    preprint_only: int = 0
    provider_hits: Dict[str, int] = field(default_factory=dict)
    provider_misses: Dict[str, int] = field(default_factory=dict)


def resolve_sources(
    config: AgentConfig,
    sources: List[SourceRecord],
    providers: Optional[ProviderClients] = None,
) -> tuple[List[SourceRecord], ResolveStats]:
    """Promote discovery sources into DOI-first canonical records."""
    if providers is None:
        providers = build_provider_clients(config)
    resolved: List[SourceRecord] = []
    stats = ResolveStats(total=len(sources))
    seen: Dict[str, SourceRecord] = {}
    for source in sources:
        updated = _resolve_one(config, source, providers, stats)
        canonical_id = updated.canonical_source_id or updated.source_id
        if canonical_id in seen:
            continue
        seen[canonical_id] = updated
        resolved.append(updated)
        if updated.canonical_source_id and updated.canonical_source_id.startswith("doi:"):
            stats.doi_confirmed += 1
        if updated.preprint_only:
            stats.preprint_only += 1
    return resolved, stats


def _resolve_one(
    config: AgentConfig,
    source: SourceRecord,
    providers: ProviderClients,
    stats: ResolveStats,
) -> SourceRecord:
    identifiers = source.identifiers.model_copy() if source.identifiers else IdentifierRecord()
    if not identifiers.arxiv_id:
        identifiers.arxiv_id = _extract_arxiv_id(source.source_id)
    extracted_doi = _extract_doi(source.doi, source.url, source.title, source.abstract)
    if extracted_doi:
        identifiers.doi = identifiers.doi or extracted_doi
    if config.mock_mode:
        return _apply_canonical(
            source,
            identifiers,
            canonical_work=None,
            unpaywall_work=None,
        )

    canonical_work = None
    unpaywall_work = None
    doi = identifiers.doi
    if doi:
        canonical_work = providers.crossref.get_by_doi(doi)
        _track_provider(stats, "crossref", canonical_work)
        if canonical_work is None:
            canonical_work = providers.openalex.get_by_doi(doi)
            _track_provider(stats, "openalex", canonical_work)
        if canonical_work is None:
            canonical_work = providers.semanticscholar.get_by_doi(doi)
            _track_provider(stats, "semanticscholar", canonical_work)
        unpaywall_work = providers.unpaywall.get_by_doi(doi)
        _track_provider(stats, "unpaywall", unpaywall_work)
    if canonical_work is None:
        query = _build_resolution_query(source)
        candidate = _best_candidate(query, providers)
        if candidate and candidate.doi:
            identifiers.doi = identifiers.doi or candidate.doi
            canonical_work = providers.crossref.get_by_doi(candidate.doi) or candidate
            _track_provider(stats, "crossref", canonical_work)
            unpaywall_work = providers.unpaywall.get_by_doi(candidate.doi)
            _track_provider(stats, "unpaywall", unpaywall_work)
    return _apply_canonical(source, identifiers, canonical_work, unpaywall_work)


def _apply_canonical(
    source: SourceRecord,
    identifiers: IdentifierRecord,
    canonical_work: Optional[ProviderWork],
    unpaywall_work: Optional[ProviderWork],
) -> SourceRecord:
    canonical_metadata = _metadata_from_source(source)
    if canonical_work:
        canonical_metadata = _metadata_from_provider(canonical_work, canonical_metadata)
        identifiers = _merge_identifiers(identifiers, canonical_work)
    canonical_source_id = None
    preprint_only = False
    if identifiers.doi:
        canonical_source_id = f"doi:{normalize_doi(identifiers.doi)}"
    elif identifiers.arxiv_id:
        canonical_source_id = f"arxiv:{identifiers.arxiv_id}"
        preprint_only = True
    else:
        canonical_source_id = source.source_id
        preprint_only = True
    evidence_links = _build_evidence_links(source, canonical_work, unpaywall_work)
    return source.model_copy(
        update={
            "identifiers": identifiers,
            "canonical_source_id": canonical_source_id,
            "canonical_metadata": canonical_metadata,
            "preprint_only": preprint_only,
            "evidence_links": evidence_links,
        }
    )


def _build_resolution_query(source: SourceRecord) -> str:
    parts = [source.title]
    if source.authors:
        parts.append(source.authors[0])
    if source.year:
        parts.append(str(source.year))
    return " ".join(part for part in parts if part)


def _best_candidate(query: str, providers: ProviderClients) -> Optional[ProviderWork]:
    candidates: List[ProviderWork] = []
    candidates.extend(providers.openalex.search(query))
    candidates.extend(providers.semanticscholar.search(query))
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda work: len(work.title or ""), reverse=True)
    return ranked[0]


def _metadata_from_source(source: SourceRecord) -> CanonicalMetadata:
    return CanonicalMetadata(
        title=source.title,
        authors=list(source.authors),
        year=source.year,
        venue=source.venue,
        doi=source.doi,
        url=source.url,
    )


def _metadata_from_provider(work: ProviderWork, fallback: CanonicalMetadata) -> CanonicalMetadata:
    return CanonicalMetadata(
        title=work.title or fallback.title,
        authors=work.authors or fallback.authors,
        year=work.year or fallback.year,
        venue=work.venue or fallback.venue,
        doi=work.doi or fallback.doi,
        url=work.url or fallback.url,
    )


def _merge_identifiers(identifiers: IdentifierRecord, work: ProviderWork) -> IdentifierRecord:
    data = identifiers.model_copy()
    if work.doi and not data.doi:
        data.doi = work.doi
    if "openalex_id" in work.identifiers and not data.openalex_id:
        data.openalex_id = work.identifiers.get("openalex_id")
    if "s2_paper_id" in work.identifiers and not data.s2_paper_id:
        data.s2_paper_id = work.identifiers.get("s2_paper_id")
    return data


def _build_evidence_links(
    source: SourceRecord,
    work: Optional[ProviderWork],
    unpaywall_work: Optional[ProviderWork],
) -> EvidenceLinks:
    landing = source.url
    if work and work.url:
        landing = work.url
    oa_url = unpaywall_work.url if unpaywall_work else None
    return EvidenceLinks(landing_page_url=landing, oa_url=oa_url)


def _extract_arxiv_id(source_id: str) -> Optional[str]:
    if source_id.startswith("S-ARXIV-"):
        return source_id.replace("S-ARXIV-", "")
    return None


def _extract_doi(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if not value:
            continue
        match = DOI_PATTERN.search(value)
        if match:
            return match.group(0)
    return None


def _track_provider(stats: ResolveStats, name: str, work: Optional[ProviderWork]) -> None:
    if stats.provider_hits is None or stats.provider_misses is None:
        return
    if work:
        stats.provider_hits[name] = stats.provider_hits.get(name, 0) + 1
    else:
        stats.provider_misses[name] = stats.provider_misses.get(name, 0) + 1
