from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


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

    def has_resolvable_locator(self) -> bool:
        return bool(self.doi or self.url)

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
