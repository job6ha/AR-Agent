from __future__ import annotations

import asyncio
from typing import List, Optional

from ..gates import gate_g2_citations
from ..schemas import AuditResult, DraftNode, SourceRecord
from ..llm_stream import StreamEmit, stream_llm_response


async def audit_citations_async(
    sources: List[SourceRecord],
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> AuditResult:
    audit = gate_g2_citations(sources, drafts)
    if llm is None:
        return audit

    prompt = (
        "You are a citation auditor. Review the draft for potential citation issues. "
        "Return a JSON array of short issue strings.\n\n"
    )
    for draft in drafts:
        prompt += f"[{draft.chapter_id}] {draft.text}\n"
    text = await stream_llm_response(
        llm,
        prompt,
        emit,
        "auditor",
        system_prompt=system_prompt,
    )
    try:
        import json

        extra_issues = json.loads(text)
        if isinstance(extra_issues, list):
            audit.issues.extend(str(item) for item in extra_issues)
            audit.passed = audit.passed and not extra_issues
    except Exception:
        pass
    return audit


def audit_citations(
    sources: List[SourceRecord],
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> AuditResult:
    return asyncio.run(
        audit_citations_async(
            sources,
            drafts,
            llm=llm,
            emit=emit,
            system_prompt=system_prompt,
        )
    )
