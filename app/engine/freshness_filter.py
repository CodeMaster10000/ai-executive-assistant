"""Post-search freshness filter for expired job postings.

Scans search result titles and snippets for expiry signals
(e.g. "this job has expired") and removes them before they
enter the pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_PATTERNS: list[str] = [
    r"no longer accepting applications",
    r"this job has expired",
    r"this listing has expired",
    r"position has been filled",
    r"this job is no longer available",
    r"posting has closed",
    r"applications? closed",
    r"no longer available",
    r"job has been removed",
]


class FreshnessFilter:
    """Removes expired job postings from search results.

    Only filters the ``job`` category by default; other categories
    pass through unchanged.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        raw_patterns = config.get("expiry_patterns", DEFAULT_EXPIRY_PATTERNS)
        self._patterns = [re.compile(p, re.IGNORECASE) for p in raw_patterns]

    def filter_results(
        self,
        results: list[dict[str, Any]],
        category: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Filter results for expiry signals.

        Returns:
            ``(kept, removed)`` tuple.  Non-job categories return
            all results in *kept* with an empty *removed* list.
        """
        if category != "job":
            return results, []

        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        for item in results:
            text = " ".join([
                item.get("title", ""),
                item.get("snippet", ""),
                item.get("body", ""),
            ])
            if self._has_expiry_signal(text):
                removed.append(item)
            else:
                kept.append(item)

        if removed:
            logger.debug(
                "FreshnessFilter removed %d expired job result(s)",
                len(removed),
            )
        return kept, removed

    def _has_expiry_signal(self, text: str) -> bool:
        return any(p.search(text) for p in self._patterns)
