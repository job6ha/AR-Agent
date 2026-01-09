from __future__ import annotations

import asyncio
from typing import List, Optional, Tuple

from ..config import AgentConfig
from ..schemas import EvidenceItem, SourceRecord
from ..llm_stream import StreamEmit, stream_llm_response


def _looks_like_refusal(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "i don't have access",
        "i do not have access",
        "unable to extract",
        "cannot provide",
        "can't provide",
        "sorry",
        "접근할 수 없",
        "원문",
        "붙여 넣",
        "paste the chapter",
        "provide the text",
    ]
    return any(pattern in lowered for pattern in patterns)


def extract_evidence(
    _config: AgentConfig,
    sources: List[SourceRecord],
    chapters: List[str],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = []
    if _config.mock_mode or llm is None:
        for chapter in chapters:
            for index, source in enumerate(sources):
                claim_id = f"{chapter}-C{index+1:03d}"
                source_id = source.canonical_source_id or source.source_id
                evidence.append(
                    EvidenceItem(
                        claim_id=claim_id,
                        source_id=source_id,
                        snippet=f"{chapter} evidence placeholder from {source.title}",
                        locator="abstract",
                        relevance_score=0.5,
                        chapter_id=chapter,
                    )
                )
        return evidence

    async def _extract_one(
        args: Tuple[str, int, SourceRecord],
    ) -> Optional[Tuple[Tuple[str, int], EvidenceItem]]:
        chapter, index, source = args
        abstract_text = (source.abstract or "").strip()
        if not abstract_text:
            return None
        snippet = abstract_text
        locator = "abstract"
        if llm is not None:
            prompt = (
                "Summarize the abstract into 1-2 concise Korean sentences. "
                "Return a JSON object with keys: snippet, locator.\n\n"
                f"Chapter: {chapter}\n"
                f"Source title: {source.title}\n"
                f"Abstract: {abstract_text}\n"
            )
            text = await stream_llm_response(
                llm,
                prompt,
                emit,
                "extractor",
                system_prompt=system_prompt,
            )
            try:
                import json

                payload = json.loads(text)
                if isinstance(payload, dict):
                    snippet = payload.get("snippet", snippet)
                    locator = payload.get("locator", locator)
            except Exception:
                snippet = text or snippet
        if snippet is None:
            snippet = ""
        if not isinstance(snippet, str):
            snippet = str(snippet)
        if not snippet or _looks_like_refusal(snippet):
            return None
        if isinstance(locator, (dict, list)):
            import json

            locator = json.dumps(locator, ensure_ascii=False)
        if locator is not None and not isinstance(locator, str):
            locator = str(locator)
        claim_id = f"{chapter}-C{index+1:03d}"
        source_id = source.canonical_source_id or source.source_id
        item = EvidenceItem(
            claim_id=claim_id,
            source_id=source_id,
            snippet=snippet,
            locator=locator or "abstract",
            relevance_score=0.5,
            chapter_id=chapter,
        )
        return (chapter, index), item

    tasks: List[Tuple[str, int, SourceRecord]] = []
    for chapter in chapters:
        for index, source in enumerate(sources):
            tasks.append((chapter, index, source))

    async def _run_all() -> List[Tuple[Tuple[str, int], EvidenceItem]]:
        if not tasks:
            return []
        semaphore = asyncio.Semaphore(max(1, _config.max_concurrency))

        async def _guarded(task: Tuple[str, int, SourceRecord]) -> Optional[Tuple[Tuple[str, int], EvidenceItem]]:
            async with semaphore:
                return await _extract_one(task)

        results = await asyncio.gather(*[_guarded(task) for task in tasks])
        return [result for result in results if result is not None]

    results = asyncio.run(_run_all())
    for _, item in sorted(results, key=lambda pair: pair[0]):
        evidence.append(item)
    return evidence
