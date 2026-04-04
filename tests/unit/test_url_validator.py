"""Unit tests for the deterministic URLValidatorAgent."""

from unittest.mock import AsyncMock

import pytest

from app.agents.url_validator import URLValidatorAgent, _MIN_BODY_CHARS


def _valid_body(extra: str = "") -> str:
    """Return a fetch result with enough content to pass the length check."""
    filler = "Lorem ipsum dolor sit amet. " * 100
    return f"HTTP 200\n\n{extra}{filler}"


def _make_state(category: str, urls: list[str]) -> dict:
    key = f"raw_{category}_results"
    return {key: [{"url": u, "title": f"Item {i}"} for i, u in enumerate(urls)]}


def _agent(side_effect=None, return_value=None) -> URLValidatorAgent:
    fetch_tool = AsyncMock()
    if side_effect is not None:
        fetch_tool.ainvoke.side_effect = side_effect
    elif return_value is not None:
        fetch_tool.ainvoke.return_value = return_value
    return URLValidatorAgent(fetch_tool=fetch_tool)


class TestDeterministicPrepass:
    @pytest.mark.asyncio
    async def test_catches_expired_job(self):
        agent = _agent(return_value=_valid_body(
            "This position is closed. No longer accepting applications. "
        ))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/111"])
        result = await agent(state)

        assert result["raw_job_results"] == []
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert result["url_validation_results"][0]["reason"] != ""

    @pytest.mark.asyncio
    async def test_catches_ended_event(self):
        agent = _agent(return_value=_valid_body("This event has ended. "))
        state = _make_state("event", ["https://example.com/event1"])
        result = await agent(state)

        assert result["raw_event_results"] == []

    @pytest.mark.asyncio
    async def test_catches_retired_cert(self):
        agent = _agent(return_value=_valid_body(
            "This course has been retired and is no longer offered. "
        ))
        state = _make_state("cert", ["https://example.com/cert1"])
        result = await agent(state)

        assert result["raw_cert_results"] == []

    @pytest.mark.asyncio
    async def test_passes_valid_job(self):
        agent = _agent(return_value=_valid_body(
            "use ai to assess how you fit. Senior Python Developer - Apply Now! "
        ))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/222"])
        result = await agent(state)

        assert "raw_job_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_catches_404(self):
        agent = _agent(return_value="HTTP 404\n\nPage not found")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/333"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_catches_fetch_error(self):
        agent = _agent(return_value="Fetch error: Connection timed out")
        state = _make_state("trend", ["https://example.com/broken"])
        result = await agent(state)

        assert result["raw_trend_results"] == []

    @pytest.mark.asyncio
    async def test_catches_exception_in_gather(self):
        agent = _agent(side_effect=RuntimeError("network down"))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/444"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_catches_short_content(self):
        agent = _agent(return_value="HTTP 200\n\nShort page.")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/555"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        agent = _agent(return_value=_valid_body("NO LONGER ACCEPTING APPLICATIONS "))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/666"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_filters_only_invalid_urls(self):
        async def fetch_side_effect(url):
            if "777" in url:
                return _valid_body("This job has expired. ")
            return _valid_body("use ai to assess how you fit. Great opportunity! ")

        agent = _agent(side_effect=fetch_side_effect)
        state = _make_state("job", [
            "https://www.linkedin.com/jobs/view/777",
            "https://www.linkedin.com/jobs/view/888",
        ])
        result = await agent(state)

        assert len(result["raw_job_results"]) == 1
        assert result["raw_job_results"][0]["url"] == "https://www.linkedin.com/jobs/view/888"
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert result["url_validation_results"][0]["reason"] != ""

    @pytest.mark.asyncio
    async def test_empty_state_returns_empty(self):
        agent = _agent(return_value="")
        result = await agent({})
        assert result == {}

    @pytest.mark.asyncio
    async def test_body_at_exact_threshold_is_valid(self):
        body = "x" * _MIN_BODY_CHARS
        agent = _agent(return_value=f"HTTP 200\n\n{body}")
        state = _make_state("trend", ["https://example.com/trend"])
        result = await agent(state)

        assert "raw_trend_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_no_fetch_tool_returns_empty(self):
        agent = URLValidatorAgent()
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/999"])
        result = await agent(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_linkedin_slug_url_passes(self):
        """LinkedIn URL with slug before numeric ID passes validation."""
        body = _valid_body("Senior Dev at BigCo. Great role! Apply now. ")
        agent = _agent(return_value=body)
        state = _make_state("job", [
            "https://www.linkedin.com/jobs/view/senior-dev-at-bigco-4390698710",
        ])
        result = await agent(state)

        assert "raw_job_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_invalid_results_include_reason(self):
        """Invalid URLs appear in url_validation_results with reason."""
        agent = _agent(return_value="HTTP 404\n\nPage not found")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/12345"])
        result = await agent(state)

        assert result["raw_job_results"] == []
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert "404" in result["url_validation_results"][0]["reason"]
