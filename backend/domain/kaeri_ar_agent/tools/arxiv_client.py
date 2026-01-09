from __future__ import annotations

from typing import List, Optional

import feedparser
import httpx


def query_arxiv(
    base_url: str,
    query: str,
    max_results: int,
    timeout_s: float,
    retry_count: int = 2,
    retry_backoff_s: float = 1.0,
) -> str:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
    }
    last_error: Optional[Exception] = None
    for attempt in range(retry_count + 1):
        try:
            response = httpx.get(
                base_url,
                params=params,
                timeout=timeout_s,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                import time

                time.sleep(retry_backoff_s * (attempt + 1))
    if last_error:
        raise last_error
    return ""


async def query_arxiv_async(
    base_url: str,
    query: str,
    max_results: int,
    timeout_s: float,
    retry_count: int = 2,
    retry_backoff_s: float = 1.0,
) -> str:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
    }
    last_error: Optional[Exception] = None
    for attempt in range(retry_count + 1):
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_s) as client:
                response = await client.get(base_url, params=params)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                import asyncio

                await asyncio.sleep(retry_backoff_s * (attempt + 1))
    if last_error:
        raise last_error
    return ""


def parse_arxiv_feed(feed_xml: str) -> List[dict]:
    feed = feedparser.parse(feed_xml)
    results: List[dict] = []
    for entry in feed.entries:
        arxiv_id = entry.get("id", "").split("/")[-1]
        results.append(
            {
                "source_id": f"S-ARXIV-{arxiv_id}" if arxiv_id else "S-ARXIV-UNKNOWN",
                "title": entry.get("title", "").strip(),
                "authors": [author.name for author in entry.get("authors", [])],
                "year": int(entry.get("published", "0000")[:4]) if entry.get("published") else None,
                "venue": "arXiv",
                "doi": entry.get("arxiv_doi"),
                "url": entry.get("link"),
                "abstract": entry.get("summary"),
                "trust_score": 0.6,
                "source_type": "paper",
            }
        )
    return results
