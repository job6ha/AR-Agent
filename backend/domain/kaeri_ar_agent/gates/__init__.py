from __future__ import annotations

from typing import List

from ..schemas import AuditResult, DraftNode, SourceRecord
from .g1a_consensus import gate_g1a_consensus


def gate_g1_sources(sources: List[SourceRecord]) -> AuditResult:
    issues: List[str] = []
    if not sources:
        issues.append("No sources retrieved.")
    if not any(source.has_resolvable_locator() for source in sources):
        issues.append("No source has a resolvable DOI or URL.")
    if not any(source.is_primary() for source in sources):
        issues.append("No primary sources (paper/report/official) found.")
    return AuditResult(passed=not issues, issues=issues)


def gate_g2_citations(sources: List[SourceRecord], drafts: List[DraftNode]) -> AuditResult:
    issues: List[str] = []
    canonical_ids = {source.canonical_source_id or source.source_id for source in sources}
    cited_ids = {cite for draft in drafts for cite in draft.citation_source_ids}
    missing = sorted(cited_ids - canonical_ids)
    if missing:
        issues.append(f"Missing cited sources: {', '.join(missing)}")
    if not drafts:
        issues.append("No draft content produced.")
    return AuditResult(passed=not issues, issues=issues)


__all__ = ["gate_g1_sources", "gate_g2_citations", "gate_g1a_consensus"]
