from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from ..llm_stream import StreamEmit, stream_llm_response

from ..schemas import PipelineInputs


async def refine_query_plan_async(
    inputs: PipelineInputs,
    plan_queries: Dict[str, List[str]],
    issues: List[str],
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str]]:
    if mock_mode or llm is None:
        refined = {chapter: list(queries) for chapter, queries in plan_queries.items()}
        for chapter in inputs.outline:
            refined.setdefault(chapter, [])
            refined[chapter].append(f"{chapter} technical report pdf")
            refined[chapter].append(f"{chapter} site:arxiv.org")
        return refined

    prompt = (
        "You are refining search queries for a technical report. "
        "Given the topic, chapters, and issues, propose 2-3 improved queries per chapter. "
        "Return JSON object: {chapter: [queries]}.\n\n"
        f"Topic: {inputs.topic}\n"
        f"Issues: {issues}\n"
    )
    text = await stream_llm_response(llm, prompt, emit, "refiner", system_prompt=system_prompt)
    try:
        import json

        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return plan_queries


def refine_query_plan(
    inputs: PipelineInputs,
    plan_queries: Dict[str, List[str]],
    issues: List[str],
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str]]:
    return asyncio.run(
        refine_query_plan_async(
            inputs,
            plan_queries,
            issues,
            llm=llm,
            mock_mode=mock_mode,
            emit=emit,
            system_prompt=system_prompt,
        )
    )
