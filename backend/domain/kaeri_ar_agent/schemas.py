from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class IdentifierRecord(BaseModel):
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    s2_paper_id: Optional[str] = None


class CanonicalMetadata(BaseModel):
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


class VerificationRecord(BaseModel):
    existence_score: float = 0.0
    identity_score: float = 0.0
    consensus_sources: List[str] = Field(default_factory=list)
    match_signals: Dict[str, float] = Field(default_factory=dict)


class StatusRecord(BaseModel):
    flags: List[str] = Field(default_factory=list)
    status_evidence: List[str] = Field(default_factory=list)


class EvidenceLinks(BaseModel):
    landing_page_url: Optional[str] = None
    oa_url: Optional[str] = None
    pdf_url: Optional[str] = None


class ProviderWork(BaseModel):
    provider: str
    provider_id: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    identifiers: Dict[str, str] = Field(default_factory=dict)
    status_flags: List[str] = Field(default_factory=list)
    raw: Optional[dict] = None


class SourceRecord(BaseModel):
    source_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    trust_score: float = 0.0
    retrieved_at: Optional[str] = None
    source_type: str = "paper"  # paper, report, official, web
    identifiers: IdentifierRecord = Field(default_factory=IdentifierRecord)
    canonical_source_id: Optional[str] = None
    canonical_metadata: Optional[CanonicalMetadata] = None
    verification: Optional[VerificationRecord] = None
    status: Optional[StatusRecord] = None
    evidence_links: Optional[EvidenceLinks] = None
    preprint_only: bool = False

    def has_resolvable_locator(self) -> bool:
        if self.doi or self.url:
            return True
        if self.canonical_metadata and (self.canonical_metadata.doi or self.canonical_metadata.url):
            return True
        if self.evidence_links and (self.evidence_links.landing_page_url or self.evidence_links.oa_url):
            return True
        return False

    def is_primary(self) -> bool:
        return self.source_type in {"paper", "report", "official"}


class EvidenceItem(BaseModel):
    claim_id: str
    source_id: str
    snippet: str
    locator: Optional[str] = None
    relevance_score: float = 0.0
    chapter_id: Optional[str] = None


class DraftNode(BaseModel):
    chapter_id: str
    paragraph_id: str
    text: str
    claim_ids: List[str] = Field(default_factory=list)
    citation_source_ids: List[str] = Field(default_factory=list)


class AuditResult(BaseModel):
    passed: bool
    issues: List[str] = Field(default_factory=list)


class PipelineInputs(BaseModel):
    raw_prompt: str = ""
    topic: str
    outline: List[str]
    scope: Optional[str] = None
    exclusions: List[str] = Field(default_factory=list)
    template_id: str = "ar-report-template"
    language: str = "ko"
    style: str = "technical"
