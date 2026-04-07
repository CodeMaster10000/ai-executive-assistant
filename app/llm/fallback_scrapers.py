"""Fallback web scrapers for Yahoo and Bing search (no API keys required)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TIMEOUT = 8
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def yahoo_search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Search Yahoo and return results as list of {title, url, snippet} dicts.

    Returns an empty list on any error (fallback-safe).
    """
    try:
        url = f"https://search.yahoo.com/search?p={quote_plus(query)}&n={max_results}"
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = client.get(url, follow_redirects=True)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []

        for item in soup.select("div.algo, li.algo"):
            title_el = item.select_one("h3 a, a.ac-algo")
            snippet_el = item.select_one("div.compText p, span.fc-falcon")
            if not title_el:
                continue
            href = title_el.get("href", "")
            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            if title and href:
                results.append({"title": title, "url": str(href), "snippet": snippet})
            if len(results) >= max_results:
                break

        logger.info("Yahoo search returned %d results for: %s", len(results), query)
        return results
    except Exception as exc:
        logger.warning("Yahoo search error: %s", exc)
        return []


def bing_search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Search Bing and return results as list of {title, url, snippet} dicts.

    Returns an empty list on any error (fallback-safe).
    """
    try:
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = client.get(url, follow_redirects=True)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []

        for item in soup.select("li.b_algo"):
            title_el = item.select_one("h2 a")
            snippet_el = item.select_one("div.b_caption p, p.b_lineclamp2")
            if not title_el:
                continue
            href = title_el.get("href", "")
            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            if title and href:
                results.append({"title": title, "url": str(href), "snippet": snippet})
            if len(results) >= max_results:
                break

        logger.info("Bing search returned %d results for: %s", len(results), query)
        return results
    except Exception as exc:
        logger.warning("Bing search error: %s", exc)
        return []
