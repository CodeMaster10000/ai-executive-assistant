"""Post-scraper link validator for job search results.

Checks that job URLs point to actual job postings rather than
search/query pages or generic job board indexes, and removes
invalid ones before they enter the data formatter.

When liveness checking is enabled (via policy config), also makes
HTTP requests to verify that URLs are still live and not expired.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.engine.freshness_filter import DEFAULT_EXPIRY_PATTERNS

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_PAGE_PATTERNS: list[str] = [
    r"[?&]q=",
    r"[?&]query=",
    r"[?&]keyword=",
    r"[?&]sc\.keyword=",
    r"/search\?",
    r"/results\?",
    r"/find\?",
    r"/jobs\?q=",
]

DEFAULT_REDIRECT_HOMEPAGE_PATTERNS: list[str] = [
    r"^/$",
    r"^/jobs/?$",
    r"^/careers/?$",
    r"^/search",
]

_GENERIC_INDEX_RE = re.compile(r"^/jobs/?$", re.IGNORECASE)


@dataclass
class LivenessResult:
    """Result of an HTTP liveness check for a single URL."""

    url: str
    is_alive: bool
    status_code: int | None = None
    final_url: str | None = None
    reason: str = "ok"
    check_duration_ms: float = 0.0


class LinkValidator:
    """Validates job result URLs via pattern matching and optional HTTP liveness checks.

    Only filters the ``job`` category; other categories pass through unchanged.

    When ``enabled`` is True in config, makes HTTP requests to verify URLs
    are still live and not serving expired/closed job content.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        config = config or {}

        raw_patterns = config.get("search_page_patterns", DEFAULT_SEARCH_PAGE_PATTERNS)
        self._search_patterns = [re.compile(p, re.IGNORECASE) for p in raw_patterns]

        self._liveness_enabled: bool = config.get("enabled", False)
        self._request_timeout: float = config.get("request_timeout_seconds", 5.0)
        self._batch_timeout: float = config.get("batch_timeout_seconds", 30.0)
        self._max_concurrency: int = config.get("max_concurrency", 10)
        self._dead_status_codes: set[int] = set(config.get("dead_status_codes", [404, 410]))
        self._max_body_read: int = config.get("max_body_read_bytes", 65536)

        raw_redirect = config.get("redirect_homepage_patterns", DEFAULT_REDIRECT_HOMEPAGE_PATTERNS)
        self._redirect_patterns = [re.compile(p, re.IGNORECASE) for p in raw_redirect]

        raw_expiry = config.get("expired_body_patterns", DEFAULT_EXPIRY_PATTERNS)
        self._expired_body_patterns = [re.compile(p, re.IGNORECASE) for p in raw_expiry]

        self._http_client = http_client

    async def validate_results(
        self,
        results: list[dict[str, Any]],
        category: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate result URLs with pattern matching and optional HTTP liveness checks.

        Returns:
            ``(kept, removed)`` tuple.  Non-job categories return
            all results in *kept* with an empty *removed* list.
        """
        if category != "job":
            return results, []

        candidates, removed = self._filter_search_pages(results)

        if not self._liveness_enabled or not candidates:
            return candidates, removed

        kept, http_removed = await self._check_liveness_batch(candidates)
        removed.extend(http_removed)
        return kept, removed

    # ------------------------------------------------------------------
    # URL pattern filtering
    # ------------------------------------------------------------------

    def _filter_search_pages(
        self, results: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        for item in results:
            if self._is_search_page(item.get("url", "")):
                removed.append(item)
            else:
                kept.append(item)

        if removed:
            logger.debug(
                "LinkValidator removed %d search-page URL(s) from job results",
                len(removed),
            )
        return kept, removed

    def _is_search_page(self, url: str) -> bool:
        if not url:
            return True

        parsed = urlparse(url)
        full = parsed.path + ("?" + parsed.query if parsed.query else "")

        if any(p.search(full) for p in self._search_patterns):
            return True

        if _GENERIC_INDEX_RE.match(parsed.path):
            return True

        return False

    # ------------------------------------------------------------------
    # HTTP liveness checks
    # ------------------------------------------------------------------

    async def _check_liveness_batch(
        self,
        candidates: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        semaphore = asyncio.Semaphore(self._max_concurrency)
        owns_client = self._http_client is None

        client = self._http_client or httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(self._request_timeout),
        )

        try:
            tasks = [
                self._check_single_url(client, item.get("url", ""), semaphore)
                for item in candidates
            ]
            try:
                liveness_results: list[LivenessResult] = await asyncio.wait_for(
                    asyncio.gather(*tasks),
                    timeout=self._batch_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "LinkValidator batch timeout (%.1fs) reached; "
                    "assuming remaining URLs are alive",
                    self._batch_timeout,
                )
                return candidates, []
        finally:
            if owns_client:
                await client.aclose()

        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        for item, result in zip(candidates, liveness_results):
            item["_liveness"] = {
                "is_alive": result.is_alive,
                "status_code": result.status_code,
                "final_url": result.final_url,
                "reason": result.reason,
                "check_duration_ms": round(result.check_duration_ms, 1),
            }
            if result.is_alive:
                kept.append(item)
            else:
                removed.append(item)

        if removed:
            logger.debug(
                "LinkValidator HTTP check removed %d dead URL(s): %s",
                len(removed),
                ", ".join(r.get("_liveness", {}).get("reason", "") for r in removed),
            )
        return kept, removed

    async def _check_single_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        semaphore: asyncio.Semaphore,
    ) -> LivenessResult:
        async with semaphore:
            t0 = time.monotonic()
            try:
                head_resp = await client.head(url)

                if head_resp.status_code == 405:
                    get_resp = await client.get(url)
                    return self._evaluate_response(url, get_resp, t0)

                if head_resp.status_code in self._dead_status_codes:
                    return LivenessResult(
                        url=url, is_alive=False,
                        status_code=head_resp.status_code,
                        final_url=str(head_resp.url),
                        reason=f"dead_status_{head_resp.status_code}",
                        check_duration_ms=(time.monotonic() - t0) * 1000,
                    )

                redirect_reason = self._check_redirect(url, head_resp)
                if redirect_reason:
                    return LivenessResult(
                        url=url, is_alive=False,
                        status_code=head_resp.status_code,
                        final_url=str(head_resp.url),
                        reason=redirect_reason,
                        check_duration_ms=(time.monotonic() - t0) * 1000,
                    )

                # Follow up with GET to check body for expiry patterns
                get_resp = await client.get(url)
                return self._evaluate_response(url, get_resp, t0)

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
                return LivenessResult(
                    url=url, is_alive=True,
                    reason=f"network_error:{type(exc).__name__}",
                    check_duration_ms=(time.monotonic() - t0) * 1000,
                )

    def _evaluate_response(
        self,
        original_url: str,
        response: httpx.Response,
        t0: float,
    ) -> LivenessResult:
        elapsed = (time.monotonic() - t0) * 1000
        status = response.status_code
        final_url = str(response.url)

        if status in self._dead_status_codes:
            return LivenessResult(
                url=original_url, is_alive=False,
                status_code=status, final_url=final_url,
                reason=f"dead_status_{status}", check_duration_ms=elapsed,
            )

        redirect_reason = self._check_redirect(original_url, response)
        if redirect_reason:
            return LivenessResult(
                url=original_url, is_alive=False,
                status_code=status, final_url=final_url,
                reason=redirect_reason, check_duration_ms=elapsed,
            )

        body_text = response.text[:self._max_body_read]
        if any(p.search(body_text) for p in self._expired_body_patterns):
            return LivenessResult(
                url=original_url, is_alive=False,
                status_code=status, final_url=final_url,
                reason="expired_body_pattern", check_duration_ms=elapsed,
            )

        return LivenessResult(
            url=original_url, is_alive=True,
            status_code=status, final_url=final_url,
            reason="ok", check_duration_ms=elapsed,
        )

    def _check_redirect(self, original_url: str, response: httpx.Response) -> str | None:
        final_url = str(response.url)
        if final_url == original_url:
            return None
        final_path = urlparse(final_url).path
        if any(p.match(final_path) for p in self._redirect_patterns):
            return "redirect_to_homepage"
        return None
