"""Tests for search tool fallback chain and fallback scrapers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.search_tool import SafeDuckDuckGoSearchTool, _format_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool(**overrides) -> SafeDuckDuckGoSearchTool:
    """Build a SafeDuckDuckGoSearchTool bypassing the ddgs validator."""
    defaults = {
        "max_results": 3,
        "region": "wt-wt",
        "timelimit": "m",
        "fallback_configs": [
            {"provider": "brave", "api_key": "test-key"},
            {"provider": "yahoo"},
            {"provider": "bing"},
        ],
        "retry_delay": 0.0,  # no delay in tests
    }
    defaults.update(overrides)
    return SafeDuckDuckGoSearchTool.model_construct(**defaults)


_DDG_RESULTS = [
    {"title": "DDG Result", "href": "https://ddg.example.com", "body": "DDG snippet"},
]

_BRAVE_RESULTS = "Title: Brave Result\nURL: https://brave.example.com\nSnippet: Brave snippet"

_YAHOO_RESULTS = [
    {"title": "Yahoo Result", "url": "https://yahoo.example.com", "snippet": "Yahoo snippet"},
]

_BING_RESULTS = [
    {"title": "Bing Result", "url": "https://bing.example.com", "snippet": "Bing snippet"},
]


def _make_ratelimit_exc():
    """Create a ddgs RatelimitException."""
    from ddgs.exceptions import RatelimitException
    return RatelimitException()


# ---------------------------------------------------------------------------
# _format_results
# ---------------------------------------------------------------------------

class TestFormatResults:
    def test_formats_ddg_style(self):
        results = [{"title": "T1", "href": "http://a.com", "body": "S1"}]
        out = _format_results(results)
        assert "Title: T1" in out
        assert "URL: http://a.com" in out
        assert "Snippet: S1" in out

    def test_formats_scraper_style(self):
        results = [{"title": "T2", "url": "http://b.com", "snippet": "S2"}]
        out = _format_results(results)
        assert "Title: T2" in out
        assert "URL: http://b.com" in out
        assert "Snippet: S2" in out

    def test_multiple_results_separated(self):
        results = [
            {"title": "A", "url": "http://a.com", "snippet": "Sa"},
            {"title": "B", "url": "http://b.com", "snippet": "Sb"},
        ]
        out = _format_results(results)
        assert out.count("Title:") == 2


# ---------------------------------------------------------------------------
# DDG retry on rate-limit
# ---------------------------------------------------------------------------

class TestDDGRetry:
    def test_retry_succeeds(self):
        """DDG rate-limited on first call, succeeds on retry."""
        tool = _make_tool()
        call_count = 0

        def mock_ddg_search(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_ratelimit_exc()
            return _DDG_RESULTS

        tool._ddg_search = mock_ddg_search
        result = tool._run("test query")
        assert call_count == 2
        assert "DDG Result" in result

    def test_retry_fails_triggers_fallback(self):
        """DDG rate-limited on both calls, falls through to fallbacks."""
        tool = _make_tool()

        def always_ratelimit(query):
            raise _make_ratelimit_exc()

        tool._ddg_search = always_ratelimit
        tool._try_brave = MagicMock(return_value=_BRAVE_RESULTS)

        result = tool._run("test query")
        assert "Brave Result" in result
        tool._try_brave.assert_called_once()


# ---------------------------------------------------------------------------
# Fallback chain ordering
# ---------------------------------------------------------------------------

class TestFallbackChain:
    def test_brave_first_when_configured(self):
        """Brave is tried before Yahoo/Bing when API key is set."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())
        tool._try_brave = MagicMock(return_value=_BRAVE_RESULTS)
        tool._try_yahoo = MagicMock(return_value="")
        tool._try_bing = MagicMock(return_value="")

        result = tool._run("test")
        assert "Brave Result" in result
        tool._try_yahoo.assert_not_called()
        tool._try_bing.assert_not_called()

    def test_falls_through_to_yahoo(self):
        """Brave fails, Yahoo succeeds."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())
        tool._try_brave = MagicMock(side_effect=Exception("Brave down"))

        with patch("app.llm.fallback_scrapers.yahoo_search", return_value=_YAHOO_RESULTS):
            result = tool._run("test")

        assert "Yahoo Result" in result

    def test_falls_through_to_bing(self):
        """Brave and Yahoo fail, Bing succeeds."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())
        tool._try_brave = MagicMock(side_effect=Exception("Brave down"))

        with patch("app.llm.fallback_scrapers.yahoo_search", return_value=[]), \
             patch("app.llm.fallback_scrapers.bing_search", return_value=_BING_RESULTS):
            result = tool._run("test")

        assert "Bing Result" in result

    def test_all_fallbacks_fail(self):
        """All engines fail, returns error message."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())
        tool._try_brave = MagicMock(side_effect=Exception("down"))

        with patch("app.llm.fallback_scrapers.yahoo_search", return_value=[]), \
             patch("app.llm.fallback_scrapers.bing_search", return_value=[]):
            result = tool._run("test")

        assert "all search backends" in result

    def test_searxng_in_chain(self):
        """SearxNG is tried when configured."""
        tool = _make_tool(fallback_configs=[
            {"provider": "searxng", "instance_url": "https://searx.example.com"},
            {"provider": "yahoo"},
        ])
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())
        tool._try_searxng = MagicMock(return_value="Title: SearxNG Result\nURL: https://s.com\nSnippet: test")

        result = tool._run("test")
        assert "SearxNG Result" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_fallbacks_configured(self):
        """With empty fallback list, returns error on rate-limit."""
        tool = _make_tool(fallback_configs=[])
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())

        result = tool._run("test")
        assert "all search backends" in result

    def test_non_ratelimit_exception_no_retry(self):
        """Non-rate-limit exceptions skip retry and fallback."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(side_effect=ValueError("bad input"))
        tool._try_brave = MagicMock()

        result = tool._run("test")
        assert "Search error:" in result
        assert "bad input" in result
        tool._try_brave.assert_not_called()

    def test_ddg_success_no_fallback(self):
        """Normal DDG success, no fallback invoked."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(return_value=_DDG_RESULTS)
        tool._try_brave = MagicMock()

        result = tool._run("test")
        assert "DDG Result" in result
        tool._try_brave.assert_not_called()

    def test_ddg_empty_results(self):
        """DDG returns empty list, returns no-results message (not a fallback)."""
        tool = _make_tool()
        tool._ddg_search = MagicMock(return_value=[])

        result = tool._run("test")
        assert "No good DuckDuckGo Search Result" in result

    def test_unknown_provider_skipped(self):
        """Unknown provider in fallback_configs is skipped gracefully."""
        tool = _make_tool(fallback_configs=[
            {"provider": "nonexistent"},
            {"provider": "yahoo"},
        ])
        tool._ddg_search = MagicMock(side_effect=_make_ratelimit_exc())

        with patch("app.llm.fallback_scrapers.yahoo_search", return_value=_YAHOO_RESULTS):
            result = tool._run("test")

        assert "Yahoo Result" in result


# ---------------------------------------------------------------------------
# Fallback scrapers (Yahoo + Bing)
# ---------------------------------------------------------------------------

_YAHOO_HTML = """
<html><body>
<div class="algo">
  <h3><a href="https://example.com/1">Example Title One</a></h3>
  <div class="compText"><p>This is the first snippet.</p></div>
</div>
<div class="algo">
  <h3><a href="https://example.com/2">Example Title Two</a></h3>
  <div class="compText"><p>This is the second snippet.</p></div>
</div>
</body></html>
"""

_BING_HTML = """
<html><body>
<ol id="b_results">
<li class="b_algo">
  <h2><a href="https://bing.example.com/1">Bing Title One</a></h2>
  <div class="b_caption"><p>Bing snippet one.</p></div>
</li>
<li class="b_algo">
  <h2><a href="https://bing.example.com/2">Bing Title Two</a></h2>
  <div class="b_caption"><p>Bing snippet two.</p></div>
</li>
</ol>
</body></html>
"""


class TestYahooScraper:
    def test_parses_results(self):
        mock_resp = MagicMock()
        mock_resp.text = _YAHOO_HTML
        mock_resp.raise_for_status = MagicMock()

        with patch("app.llm.fallback_scrapers.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=MagicMock(
                get=MagicMock(return_value=mock_resp)
            ))
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            from app.llm.fallback_scrapers import yahoo_search
            results = yahoo_search("test query", max_results=5)

        assert len(results) == 2
        assert results[0]["title"] == "Example Title One"
        assert results[0]["url"] == "https://example.com/1"
        assert "first snippet" in results[0]["snippet"]

    def test_returns_empty_on_error(self):
        with patch("app.llm.fallback_scrapers.httpx.Client", side_effect=Exception("network error")):
            from app.llm.fallback_scrapers import yahoo_search
            results = yahoo_search("test")

        assert results == []


class TestBingScraper:
    def test_parses_results(self):
        mock_resp = MagicMock()
        mock_resp.text = _BING_HTML
        mock_resp.raise_for_status = MagicMock()

        with patch("app.llm.fallback_scrapers.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=MagicMock(
                get=MagicMock(return_value=mock_resp)
            ))
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            from app.llm.fallback_scrapers import bing_search
            results = bing_search("test query", max_results=5)

        assert len(results) == 2
        assert results[0]["title"] == "Bing Title One"
        assert results[0]["url"] == "https://bing.example.com/1"
        assert "Bing snippet one" in results[0]["snippet"]

    def test_returns_empty_on_error(self):
        with patch("app.llm.fallback_scrapers.httpx.Client", side_effect=Exception("timeout")):
            from app.llm.fallback_scrapers import bing_search
            results = bing_search("test")

        assert results == []
