from __future__ import annotations

import asyncio
import re
from typing import Dict, List, Optional

from ..schemas import DraftNode
from ..llm_stream import StreamEmit, stream_llm_response


async def compose_text_async(
    drafts: List[DraftNode],
    sources: List[Dict],
    plan_queries: Optional[Dict[str, List[str]]] = None,
    scope: Optional[str] = None,
    exclusions: Optional[List[str]] = None,
    retrieval_stats: Optional[Dict[str, int]] = None,
    evidence_stats: Optional[Dict[str, int]] = None,
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> str:
    sections: List[str] = []
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

        keyword_prompt = (
            "Generate 3-6 concise Korean keywords for the report. "
            "Return as a comma-separated list only.\n\n"
        )
        for draft in drafts:
            keyword_prompt += f"[{draft.chapter_id}] {draft.text}\n"
        keywords = await stream_llm_response(
            llm,
            keyword_prompt,
            emit,
            "composer",
            system_prompt=system_prompt,
        )
        sections.append(f"**키워드**: {keywords.strip()}\n")
    for draft in drafts:
        sections.append(f"## {draft.chapter_id}\n{draft.text}\n")

    if scope or exclusions:
        scope_lines = ["## 범위", scope or ""]
        if exclusions:
            scope_lines.append(f"제외 범위: {', '.join(exclusions)}")
        sections.append("\n".join(scope_lines) + "\n")

    if plan_queries:
        method_lines = ["## 방법론", "검색 쿼리 및 선정 기준 요약"]
        for chapter, queries in plan_queries.items():
            limited = ", ".join(queries[:3])
            method_lines.append(f"- {chapter}: {limited}")
        if retrieval_stats:
            method_lines.append(
                f"- 검색 쿼리 수: {retrieval_stats.get('total_queries', 0)}"
            )
            method_lines.append(
                f"- 수집 문헌 수: {retrieval_stats.get('retrieved_sources', 0)}"
            )
        if evidence_stats:
            method_lines.append(
                f"- 추출된 근거 스니펫 수: {evidence_stats.get('evidence_items', 0)}"
            )
        sections.append("\n".join(method_lines) + "\n")

    used_ids: List[str] = []
    for draft in drafts:
        for source_id in draft.citation_source_ids:
            if source_id not in used_ids:
                used_ids.append(source_id)
    source_map = {}
    for source in sources:
        canonical_id = source.get("canonical_source_id") or source.get("source_id")
        source_map[canonical_id] = source

    def _format_ref(index: int, source: Dict) -> str:
        metadata = source.get("canonical_metadata") or {}
        authors = ", ".join(metadata.get("authors") or source.get("authors") or [])
        if authors:
            authors = f"{authors}. "
        year = metadata.get("year") or source.get("year") or "n.d."
        title = metadata.get("title") or source.get("title") or source.get("source_id")
        venue = metadata.get("venue") or source.get("venue") or ""
        link = metadata.get("doi") or source.get("doi") or metadata.get("url") or source.get("url") or ""
        preprint_only = source.get("preprint_only")
        label = "[preprint] " if preprint_only else ""
        parts = [f"[{index}] ", authors, f"({year}). ", f"{title}. "]
        if venue:
            parts.append(f"{venue}. ")
        if link:
            parts.append(f"{link}")
        return (label + "".join(parts)).strip()

    citation_index = {sid: idx + 1 for idx, sid in enumerate(used_ids)}
    text = "\n".join(sections)
    for source_id, idx in citation_index.items():
        text = text.replace(source_id, f"[{idx}]")
    text = re.sub(r"\(\[", "[", text)
    text = re.sub(r"\]\)", "]", text)

    if used_ids:
        references = ["## 참고문헌"]
        for source_id in used_ids:
            source = source_map.get(source_id)
            if not source:
                continue
            references.append(_format_ref(citation_index[source_id], source))
        text += "\n" + "\n".join(references) + "\n"
    return text


def compose_text(
    drafts: List[DraftNode],
    sources: List[Dict],
    plan_queries: Optional[Dict[str, List[str]]] = None,
    scope: Optional[str] = None,
    exclusions: Optional[List[str]] = None,
    retrieval_stats: Optional[Dict[str, int]] = None,
    evidence_stats: Optional[Dict[str, int]] = None,
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
    system_prompt: str = "",
) -> str:
    return asyncio.run(
        compose_text_async(
            drafts,
            sources,
            plan_queries=plan_queries,
            scope=scope,
            exclusions=exclusions,
            retrieval_stats=retrieval_stats,
            evidence_stats=evidence_stats,
            llm=llm,
            emit=emit,
            system_prompt=system_prompt,
        )
    )
