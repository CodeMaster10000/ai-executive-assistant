"""DuckDuckGo search tool with fallback chain for rate-limit resilience.

Fallback order: retry DDG -> Brave -> SearxNG -> Yahoo -> Bing.
Brave/SearxNG require config (API key / instance URL); Yahoo/Bing are
always available as scrapers with no API key.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import Field, model_validator

logger = logging.getLogger(__name__)

# Engines to never use (encyclopedia-style, not real web search;
# the "auto" backend in ddgs v8 hits wt.wikipedia.org which is unreachable)
_BLOCKED_ENGINES = frozenset({"wikipedia", "grokipedia"})

# Preferred engine order: Google first for best results, then DuckDuckGo
_PREFERRED_ORDER = ["google", "duckduckgo", "brave", "yahoo", "mojeek", "yandex"]


def _format_results(results: list[dict[str, str]]) -> str:
    """Format a list of {title, url, snippet} dicts into the standard output."""
    return "\n\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('url', r.get('href', ''))}\nSnippet: {r.get('snippet', r.get('body', ''))}"
        for r in results
    )


class SafeDuckDuckGoSearchTool(BaseTool):
    """Web search via DuckDuckGo with automatic fallback on rate-limit.

    duckduckgo-search v8 prioritises Wikipedia as the first text engine
    in ``backend="auto"``, which hits unreliable regional Wikipedia
    subdomains (e.g. ``wt.wikipedia.org`` for region ``wt-wt``).
    This tool builds an explicit backend list from all available engines
    minus the blocked ones so Wikipedia is never contacted.

    When DDG rate-limits, the tool retries once after a short delay,
    then tries each configured fallback engine in order until one succeeds.
    """

    name: str = "duckduckgo_search"
    description: str = (
        "Search the web using DuckDuckGo. "
        "Input should be a search query string."
    )
    max_results: int = Field(default=10, description="Max results to return")
    region: str = Field(default="wt-wt", description="Search region")
    timelimit: str = Field(default="", description="Time filter: d (day), w (week), m (month), y (year)")
    fallback_configs: list[dict[str, str]] = Field(
        default_factory=list,
        description="Ordered fallback configs: [{'provider': 'brave', 'api_key': '...'}, {'provider': 'yahoo'}, ...]",
    )
    retry_delay: float = Field(default=2.0, description="Seconds to wait before retrying DDG")
    _backend: str = ""

    @model_validator(mode="after")
    def _resolve_backends(self) -> "SafeDuckDuckGoSearchTool":
        from ddgs.engines import ENGINES

        available = set(ENGINES.get("text", {})) - _BLOCKED_ENGINES
        ordered = [e for e in _PREFERRED_ORDER if e in available]
        # Append any new engines not in our preferred list
        ordered += sorted(available - set(ordered))
        self._backend = ",".join(ordered)
        logger.info("SafeDuckDuckGoSearchTool backends: %s", self._backend)
        if self.fallback_configs:
            providers = [c["provider"] for c in self.fallback_configs]
            logger.info("Search fallback chain: %s", " -> ".join(providers))
        return self

    def _ddg_search(self, query: str) -> list[dict[str, Any]]:
        """Execute the raw DDG search, letting exceptions propagate."""
        from ddgs import DDGS

        kwargs: dict[str, Any] = {
            "region": self.region,
            "safesearch": "moderate",
            "max_results": self.max_results,
            "backend": self._backend,
        }
        if self.timelimit:
            kwargs["timelimit"] = self.timelimit
        with DDGS() as ddgs:
            return ddgs.text(query, **kwargs)

    def _try_brave(self, query: str, api_key: str) -> str:
        """Try Brave Search via langchain-community wrapper."""
        from langchain_community.utilities import BraveSearchWrapper

        wrapper = BraveSearchWrapper(api_key=api_key, search_kwargs={"count": self.max_results})
        raw = wrapper.run(query)
        if raw:
            logger.info("Brave Search returned results for: %s", query)
            return raw
        return ""

    def _try_searxng(self, query: str, instance_url: str) -> str:
        """Try SearxNG via langchain-community wrapper."""
        from langchain_community.utilities import SearxSearchWrapper

        wrapper = SearxSearchWrapper(searx_host=instance_url)
        raw = wrapper.run(query, engines=["google", "bing", "duckduckgo"])
        if raw:
            logger.info("SearxNG returned results for: %s", query)
            return raw
        return ""

    def _try_yahoo(self, query: str) -> str:
        """Try Yahoo Search via custom scraper."""
        from app.llm.fallback_scrapers import yahoo_search

        results = yahoo_search(query, max_results=self.max_results)
        if results:
            return _format_results(results)
        return ""

    def _try_bing(self, query: str) -> str:
        """Try Bing via custom scraper."""
        from app.llm.fallback_scrapers import bing_search

        results = bing_search(query, max_results=self.max_results)
        if results:
            return _format_results(results)
        return ""

    def _search_with_fallbacks(self, query: str) -> str:
        """Try each configured fallback in order, return first success."""
        for cfg in self.fallback_configs:
            provider = cfg["provider"]
            try:
                result = ""
                if provider == "brave":
                    result = self._try_brave(query, cfg.get("api_key", ""))
                elif provider == "searxng":
                    result = self._try_searxng(query, cfg.get("instance_url", ""))
                elif provider == "yahoo":
                    result = self._try_yahoo(query)
                elif provider == "bing":
                    result = self._try_bing(query)
                else:
                    logger.warning("Unknown fallback provider: %s", provider)
                    continue

                if result:
                    logger.info("Fallback '%s' succeeded for: %s", provider, query)
                    return result
                logger.info("Fallback '%s' returned no results for: %s", provider, query)
            except Exception as exc:
                logger.warning("Fallback '%s' failed: %s", provider, exc)
                continue

        return "Search error: all search backends rate-limited or unavailable"

    def _run(self, query: str) -> str:
        from ddgs.exceptions import RatelimitException

        try:
            results = self._ddg_search(query)
            if not results:
                return "No good DuckDuckGo Search Result was found"
            return _format_results(results)
        except RatelimitException as exc:
            logger.warning("DuckDuckGo rate-limited, retrying in %.1fs: %s", self.retry_delay, exc)
            time.sleep(self.retry_delay)
            # One retry before falling back
            try:
                results = self._ddg_search(query)
                if results:
                    logger.info("DuckDuckGo retry succeeded for: %s", query)
                    return _format_results(results)
            except Exception:
                pass
            # DDG retry failed, try fallbacks
            logger.info("DuckDuckGo retry failed, trying fallback chain for: %s", query)
            return self._search_with_fallbacks(query)
        except Exception as exc:
            logger.warning("DuckDuckGo search error: %s", exc)
            return f"Search error: {exc}"

    async def _arun(self, query: str) -> str:
        return await asyncio.to_thread(self._run, query)
