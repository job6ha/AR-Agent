from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..llm_stream import StreamEmit, stream_llm_response


async def generate_outline_async(
    prompt: str,
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str] | str]:
    if mock_mode or llm is None:
        return {
            "topic": "원자력 다중물리해석을 위한 AI 기반 시뮬레이션 최신 기술 동향 보고서",
            "outline": [
                "관련 최신 기술동향",
                "원자력 분야 시뮬레이션 인공지능 사례",
                "노심 및 열수력 해석 난제",
                "멀티 피직스 결합 난제",
                "AI 모델 결합 시 난제",
                "연구 방향 제시",
            ],
        }

    prompt_text = (
        "You are an outline designer for a technical Korean report. "
        "Given the user prompt, generate a concise report topic and 5-7 chapter headings. "
        "Return JSON object only: {\"topic\": \"...\", \"outline\": [\"...\", ...]}.\n\n"
        f"User prompt:\n{prompt}\n"
    )
    text = await stream_llm_response(llm, prompt_text, emit, "outliner", system_prompt=system_prompt)
    try:
        import json

        payload = json.loads(text)
        topic = payload.get("topic", "AR 기술동향 보고서")
        outline = payload.get("outline", [])
        scope = payload.get("scope")
        exclusions = payload.get("exclusions", [])
        if isinstance(outline, list) and outline:
            return {
                "topic": topic,
                "outline": outline,
                "scope": scope,
                "exclusions": exclusions if isinstance(exclusions, list) else [],
            }
    except Exception:
        pass
    return {"topic": "AR 기술동향 보고서", "outline": [], "scope": None, "exclusions": []}


def generate_outline(
    prompt: str,
    llm: Optional[object] = None,
    mock_mode: bool = True,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> Dict[str, List[str] | str]:
    return asyncio.run(
        generate_outline_async(
            prompt,
            llm=llm,
            mock_mode=mock_mode,
            emit=emit,
            system_prompt=system_prompt,
        )
    )
