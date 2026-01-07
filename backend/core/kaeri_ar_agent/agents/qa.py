from __future__ import annotations

import asyncio
from typing import List, Optional

from ..schemas import DraftNode
from ..llm_stream import StreamEmit, stream_llm_response


async def qa_checks_async(
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> List[str]:
    issues: List[str] = []
    if not drafts:
        issues.append("Draft output is empty.")
    for draft in drafts:
        if "입니다" in draft.text:
            issues.append(f"Honorific found in {draft.chapter_id}.")
    if llm is None:
        return issues

    prompt = (
        "You are a QA reviewer for a Korean technical report. "
        "Check for style violations (honorifics, missing required sections). "
        "Return a JSON array of issues.\n\n"
    )
    for draft in drafts:
        prompt += f"[{draft.chapter_id}] {draft.text}\n"
    text = await stream_llm_response(llm, prompt, emit, "qa", system_prompt=system_prompt)
    try:
        import json

        extra_issues = json.loads(text)
        if isinstance(extra_issues, list):
            issues.extend(str(item) for item in extra_issues)
    except Exception:
        pass
    return issues


def qa_checks(
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> List[str]:
    return asyncio.run(
        qa_checks_async(drafts, llm=llm, emit=emit, system_prompt=system_prompt)
    )
