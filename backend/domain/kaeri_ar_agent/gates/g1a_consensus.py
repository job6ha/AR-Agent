from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from ..config import AgentConfig
from ..providers import ProviderClients, build_provider_clients
from ..schemas import AuditResult, ProviderWork, SourceRecord, VerificationRecord


@dataclass
class ConsensusResult:
    sources: List[SourceRecord]
    pending: List[SourceRecord]
    rejected: List[SourceRecord]
    audit: AuditResult


def gate_g1a_consensus(
    config: AgentConfig,
    sources: List[SourceRecord],
    providers: Optional[ProviderClients] = None,
) -> ConsensusResult:
    """Score sources against multi-provider consensus and gate them."""
    if providers is None:
        providers = build_provider_clients(config)
    passed: List[SourceRecord] = []
    pending: List[SourceRecord] = []
    rejected: List[SourceRecord] = []
    issues: List[str] = []
    for source in sources:
        updated = _score_source(config, source, providers)
        score = updated.verification.identity_score if updated.verification else 0.0
        if score >= 0.85:
            passed.append(updated)
        elif score >= 0.60:
            pending.append(updated)
        else:
            rejected.append(updated)
    if pending:
        issues.append(f"Consensus pending for {len(pending)} sources.")
    if rejected:
        issues.append(f"Consensus rejected for {len(rejected)} sources.")
    audit = AuditResult(passed=not issues, issues=issues)
    return ConsensusResult(sources=passed, pending=pending, rejected=rejected, audit=audit)


def _score_source(
    config: AgentConfig,
    source: SourceRecord,
    providers: ProviderClients,
) -> SourceRecord:
    if config.mock_mode:
        verification = VerificationRecord(
            existence_score=1.0,
            identity_score=0.9,
            consensus_sources=["mock"],
            match_signals={"doi_match": 0.6, "title_sim": 0.2, "first_author": 0.1, "year": 0.05, "venue": 0.05},
        )
        return source.model_copy(update={"verification": verification})
    canonical = source.canonical_metadata
    doi = canonical.doi if canonical else source.doi
    works: List[ProviderWork] = []
    if doi:
        crossref = providers.crossref.get_by_doi(doi)
        if crossref:
            works.append(crossref)
        openalex = providers.openalex.get_by_doi(doi)
        if openalex:
            works.append(openalex)
        s2 = providers.semanticscholar.get_by_doi(doi)
        if s2:
            works.append(s2)
    else:
        query = _resolution_query(source)
        works.extend(providers.openalex.search(query))
        works.extend(providers.semanticscholar.search(query))
    consensus_sources = sorted({work.provider for work in works})
    signals = _match_signals(source, canonical, works)
    score = _score_from_signals(signals)
    existence_score = 1.0 if works else 0.0
    if _should_force_reject(signals):
        score = 0.0
    if doi and len(consensus_sources) < 2:
        score = min(score, 0.7)
    verification = VerificationRecord(
        existence_score=existence_score,
        identity_score=score,
        consensus_sources=consensus_sources,
        match_signals=signals,
    )
    return source.model_copy(update={"verification": verification})


def _resolution_query(source: SourceRecord) -> str:
    parts = [source.title]
    if source.authors:
        parts.append(source.authors[0])
    if source.year:
        parts.append(str(source.year))
    return " ".join(part for part in parts if part)


def _match_signals(
    source: SourceRecord,
    canonical,
    works: List[ProviderWork],
) -> Dict[str, float]:
    base_title = canonical.title if canonical else source.title
    base_authors = canonical.authors if canonical else source.authors
    base_year = canonical.year if canonical else source.year
    base_venue = canonical.venue if canonical else source.venue
    base_doi = canonical.doi if canonical else source.doi
    best_title = 0.0
    best_venue = 0.0
    doi_match = 0.0
    author_match = 0.0
    year_match = 0.0
    for work in works:
        if base_doi and work.doi and base_doi.lower() == work.doi.lower():
            doi_match = 0.6
        best_title = max(best_title, _similarity(base_title, work.title))
        best_venue = max(best_venue, _similarity(base_venue, work.venue))
        if base_year and work.year and base_year == work.year:
            year_match = 0.05
        if base_authors and work.authors:
            if _first_author_last(base_authors) == _first_author_last(work.authors):
                author_match = 0.1
    return {
        "doi_match": doi_match,
        "title_sim": best_title * 0.2,
        "first_author": author_match,
        "year": year_match,
        "venue": best_venue * 0.05,
    }


def _score_from_signals(signals: Dict[str, float]) -> float:
    return round(sum(signals.values()), 3)


def _similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _normalize(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace()).strip()


def _first_author_last(authors: List[str]) -> str:
    if not authors:
        return ""
    parts = authors[0].split()
    return parts[-1].lower() if parts else ""


def _should_force_reject(signals: Dict[str, float]) -> bool:
    if signals.get("doi_match", 0.0) == 0.0:
        return False
    title_sim = signals.get("title_sim", 0.0)
    author_match = signals.get("first_author", 0.0)
    year_match = signals.get("year", 0.0)
    return title_sim < 0.1 and author_match == 0.0 and year_match == 0.0
