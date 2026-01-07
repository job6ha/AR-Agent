from __future__ import annotations

from typing import Dict, List, Optional
from typing_extensions import TypedDict

from .schemas import AuditResult, DraftNode, EvidenceItem, PipelineInputs, SourceRecord


class PipelineState(TypedDict, total=False):
    inputs: PipelineInputs
    plan_queries: Dict[str, List[str]]
    sources: List[SourceRecord]
    evidence: List[EvidenceItem]
    drafts: List[DraftNode]
    audit: Optional[AuditResult]
    composed_text: Optional[str]
    gates: Dict[str, bool]
    errors: List[str]
    warnings: List[str]
    iteration: int
    max_iterations: int
    last_issues: List[str]
    prompts: Dict[str, str]
    g2_route: Optional[str]
    qa_route: Optional[str]
    retrieval_stats: Dict[str, int]
    evidence_stats: Dict[str, int]
