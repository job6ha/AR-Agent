from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional


StreamEmit = Callable[[str, str, Optional[Dict[str, Any]]], None]


async def stream_llm_response(
    llm: Any,
    prompt: str,
    emit: Optional[StreamEmit],
    agent: str,
    system_prompt: Optional[str] = None,
) -> str:
    stream_id = uuid.uuid4().hex
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{prompt}"
    if emit:
        emit(
            agent,
            "llm stream started",
            {
                "type": "llm_stream_start",
                "stream_id": stream_id,
                "prompt": full_prompt,
                "system_prompt": system_prompt or "",
                "user_prompt": prompt,
            },
        )
    chunks = []
    async for chunk in llm.astream(full_prompt):
        text = getattr(chunk, "content", str(chunk))
        if text:
            chunks.append(text)
            if emit:
                emit(
                    agent,
                    "llm stream chunk",
                    {"type": "llm_stream", "stream_id": stream_id, "delta": text},
                )
        await asyncio.sleep(0)
    full_text = "".join(chunks)
    if emit:
        emit(
            agent,
            "llm stream completed",
            {"type": "llm_stream_end", "stream_id": stream_id, "length": len(full_text)},
        )
    return full_text
