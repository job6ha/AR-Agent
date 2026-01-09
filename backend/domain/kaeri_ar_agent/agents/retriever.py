from __future__ import annotations

from datetime import datetime
import asyncio
from typing import Dict, List, Optional, Tuple

from ..config import AgentConfig
from ..schemas import SourceRecord
from ..tools.arxiv_client import query_arxiv, query_arxiv_async, parse_arxiv_feed
from ..llm_stream import StreamEmit, stream_llm_response


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def _rank_sources_with_embeddings(
    config: AgentConfig,
    plan_queries: Dict[str, List[str]],
    sources: List[SourceRecord],
) -> List[SourceRecord]:
    if not sources:
        return sources
    embeddings = config.build_embeddings()
    source_texts = [
        f"{source.title}\n{source.abstract or ''}".strip() for source in sources
    ]
    source_vectors = await embeddings.aembed_documents(source_texts)

    chapters = list(plan_queries.keys())
    if not chapters:
        return sources[: config.max_sources]
    per_chapter = max(1, config.max_sources // max(1, len(chapters)))

    selected_ids: List[str] = []
    for chapter in chapters:
        query_text = " ".join(plan_queries.get(chapter, []))[: config.max_query_length]
        query_vector = await embeddings.aembed_query(query_text)
        scored = sorted(
            zip(sources, source_vectors),
            key=lambda pair: _cosine_similarity(query_vector, pair[1]),
            reverse=True,
        )
        for source, _ in scored[:per_chapter]:
            if source.source_id not in selected_ids:
                selected_ids.append(source.source_id)
    id_set = set(selected_ids)
    ranked = [source for source in sources if source.source_id in id_set]
    return ranked[: config.max_sources]


async def _fetch_one(
    config: AgentConfig,
    query: str,
) -> List[SourceRecord]:
    try:
        feed_xml = await query_arxiv_async(
            config.arxiv_base_url,
            query,
            config.max_sources,
            config.request_timeout_s,
            retry_count=config.request_retry_count,
            retry_backoff_s=config.request_retry_backoff_s,
        )
    except Exception:
        return []
    sources: List[SourceRecord] = []
    for entry in parse_arxiv_feed(feed_xml):
        sources.append(SourceRecord(**entry))
    return sources


async def retrieve_sources_async(
    config: AgentConfig,
    plan_queries: Dict[str, List[str]],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
) -> List[SourceRecord]:
    if config.mock_mode:
        return [
            SourceRecord(
                source_id="S-ARXIV-0001",
                title="Coupled AI-physics modeling for multi-physics nuclear simulation",
                authors=["Kim", "Lee"],
                year=2024,
                venue="arXiv",
                doi="10.48550/arXiv.0000.0000",
                url="https://arxiv.org/abs/0000.0000",
                trust_score=0.7,
                retrieved_at=datetime.utcnow().isoformat(),
                source_type="paper",
            )
        ]

    tasks: List[asyncio.Task[List[SourceRecord]]] = []
    for queries in plan_queries.values():
        limited_queries = queries[: config.max_queries_per_chapter]
        for query in limited_queries:
            sanitized_query = query[: config.max_query_length]
            tasks.append(asyncio.create_task(_fetch_one(config, sanitized_query)))
    sources: List[SourceRecord] = []
    if tasks:
        results = await asyncio.gather(*tasks)
        for chunk in results:
            sources.extend(chunk)
    if config.mock_mode:
        return sources[: config.max_sources]
    return await _rank_sources_with_embeddings(config, plan_queries, sources)


def retrieve_sources(
    config: AgentConfig,
    plan_queries: Dict[str, List[str]],
    llm: Optional[object] = None,
    emit: Optional[StreamEmit] = None,
) -> List[SourceRecord]:
    return asyncio.run(retrieve_sources_async(config, plan_queries, llm=llm, emit=emit))
