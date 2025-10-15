from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

from .config import settings
from .llm import simple_chat


def _client() -> TavilyClient:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env.")
    return TavilyClient(api_key=settings.tavily_api_key)


def _compress_query_if_needed(prompt: str) -> str:
    # Tavily max query length ~400 chars; keep buffer
    if len(prompt) <= 350:
        return prompt
    try:
        system = (
            "Condense the user's research brief into a <=300 char search query with key terms and entities. "
            "Keep critical company names and concepts. Output only the query text."
        )
        q = simple_chat(system, prompt)
        q = (q or "").strip()
        if len(q) > 350:
            q = q[:350]
        return q or prompt[:350]
    except Exception:
        return prompt[:350]


def initial_research(prompt: str, max_results: int = 3) -> Dict[str, Any]:
    """Top-line research for a prompt, including images when available."""
    client = _client()
    q = _compress_query_if_needed(prompt)
    res = client.search(
        query=q,
        topic="news",
        time_range="week",
        max_results=max_results,
        include_images=True,
        include_raw_content=True,
    )
    return res


def research_topics(topic: str, time_range: str = "month") -> Dict[str, Any]:
    client = _client()
    # Normalize/expand very short topics so Tavily doesn't reject the query
    t = (topic or "").strip()
    # Remove non-word chars to assess actual length
    import re
    alnum_len = len(re.sub(r"\W", "", t))
    if alnum_len < 2:
        # Fallback to a broad but specific AV query
        q = (
            "autonomous vehicle industry updates last month regulatory safety Waymo Zoox Tesla robotaxi city deployments"
        )
    elif len(t) < 8:
        # Short topic: enrich with AV context and key entities
        q = (
            f"{t} autonomous vehicle industry news regulatory updates safety Waymo Zoox Tesla robotaxi city deployments last month"
        )
    else:
        q = t
    res = client.search(
        query=q,
        time_range=time_range,
        include_images=True,
        include_raw_content=True,
    )
    return res
