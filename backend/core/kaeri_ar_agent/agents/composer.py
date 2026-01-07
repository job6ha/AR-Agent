from __future__ import annotations

import asyncio
from typing import List, Optional

from ..schemas import DraftNode
from ..llm_stream import StreamEmit, stream_llm_response


async def compose_text_async(
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> str:
    sections = []
    if llm is not None:
        prompt = (
            "Create a short abstract in Korean for the report based on the draft sections. "
            "Return a single paragraph.\n\n"
        )
        for draft in drafts:
            prompt += f"[{draft.chapter_id}] {draft.text}\n"
        abstract = await stream_llm_response(
            llm,
            prompt,
            emit,
            "composer",
            system_prompt=system_prompt,
        )
        sections.append(f"## 초록\n{abstract}\n")
    for draft in drafts:
        sections.append(f"## {draft.chapter_id}\n{draft.text}\n")
    return "\n".join(sections)


def compose_text(
    drafts: List[DraftNode],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> str:
    return asyncio.run(compose_text_async(drafts, llm=llm, emit=emit, system_prompt=system_prompt))
