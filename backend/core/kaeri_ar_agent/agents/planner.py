from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

from ..schemas import PipelineInputs
from ..llm_stream import StreamEmit, stream_llm_response


async def _plan_one(
    chapter: str,
    inputs: PipelineInputs,
    llm: object,
    emit: Optional[StreamEmit],
    system_prompt: str,
) -> Tuple[str, List[str]]:
    prompt = (
        "You are a research query planner. "
        "Generate 3-5 concise search queries for the chapter topic below. "
        "Return as a JSON array of strings only.\n\n"
        f"Topic: {inputs.topic}\n"
        f"Chapter: {chapter}\n"
    )
    text = await stream_llm_response(llm, prompt, emit, "planner", system_prompt=system_prompt)
    queries: List[str] = []
    try:
        import json

        queries = json.loads(text)
    except Exception:
        queries = [f"{chapter} arxiv", f"{chapter} nuclear simulation"]
    return chapter, queries


async def build_query_plan_async(
    inputs: PipelineInputs,
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str]]:
    plan: Dict[str, List[str]] = {}
    if mock_mode or llm is None:
        for chapter in inputs.outline:
            plan[chapter] = [
                f"{chapter} arxiv",
                f"{chapter} nuclear simulation",
                f"{chapter} AI coupling",
            ]
        return plan

    tasks = [
        _plan_one(chapter, inputs, llm, emit, system_prompt)
        for chapter in inputs.outline
    ]
    results = await asyncio.gather(*tasks)
    for chapter, queries in results:
        plan[chapter] = queries
    return plan


def build_query_plan(
    inputs: PipelineInputs,
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str]]:
    return asyncio.run(
        build_query_plan_async(
            inputs,
            llm=llm,
            mock_mode=mock_mode,
            emit=emit,
            system_prompt=system_prompt,
        )
    )
