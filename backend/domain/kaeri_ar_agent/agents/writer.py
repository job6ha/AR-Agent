from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

from ..config import AgentConfig
from ..schemas import DraftNode, EvidenceItem
from ..llm_stream import StreamEmit, stream_llm_response


def write_chapters(
    _config: AgentConfig,
    topic: str,
    scope: Optional[str],
    exclusions: List[str],
    outline: List[str],
    evidence: List[EvidenceItem],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> List[DraftNode]:
    evidence_by_chapter: Dict[str, List[EvidenceItem]] = {}
    for item in evidence:
        evidence_by_chapter.setdefault(item.chapter_id or "misc", []).append(item)

    async def _write_one(chapter: str, items: List[EvidenceItem]) -> DraftNode:
        claim_ids = [item.claim_id for item in items]
        source_ids = [item.source_id for item in items]
        if _config.mock_mode or llm is None:
            text = f"{chapter}는 핵심 기술과 난제를 정리한다. ({', '.join(source_ids)})"
        else:
            prompt = (
                "You are writing a technical Korean report. "
                "Use only the evidence snippets and cite sources as (canonical_source_id). "
                "No honorifics. Return a single paragraph.\n\n"
                f"Chapter: {chapter}\n"
                f"Report topic: {topic}\n"
                f"Scope: {scope or ''}\n"
                f"Exclusions: {', '.join(exclusions) if exclusions else ''}\n"
                "Evidence:\n"
            )
            for item in items:
                prompt += f"- [{item.source_id}] {item.snippet}\n"
            text = await stream_llm_response(
                llm,
                prompt,
                emit,
                "writer",
                system_prompt=system_prompt,
            )
        return DraftNode(
            chapter_id=chapter,
            paragraph_id=f"{chapter}-P001",
            text=text,
            claim_ids=claim_ids,
            citation_source_ids=source_ids,
        )

    async def _run_all() -> List[DraftNode]:
        tasks = []
        for chapter in outline:
            chapter_evidence = evidence_by_chapter.get(chapter, [])
            tasks.append(_write_one(chapter, chapter_evidence))
        return await asyncio.gather(*tasks)

    return asyncio.run(_run_all())
