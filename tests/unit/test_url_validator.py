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
        state = _make_state("job", ["https://example.com/job1"])
        result = await agent(state)

        assert result["raw_job_results"] == []
        assert result["url_validation_results"] == []

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
            "Senior Python Developer - Apply Now! We are hiring. "
        ))
        state = _make_state("job", ["https://example.com/job1"])
        result = await agent(state)

        assert "raw_job_results" not in result
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is True

    @pytest.mark.asyncio
    async def test_catches_404(self):
        agent = _agent(return_value="HTTP 404\n\nPage not found")
        state = _make_state("job", ["https://example.com/gone"])
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
        state = _make_state("job", ["https://example.com/err"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_catches_short_content(self):
        agent = _agent(return_value="HTTP 200\n\nShort page.")
        state = _make_state("job", ["https://example.com/short"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        agent = _agent(return_value=_valid_body("NO LONGER ACCEPTING APPLICATIONS "))
        state = _make_state("job", ["https://example.com/job"])
        result = await agent(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_filters_only_invalid_urls(self):
        async def fetch_side_effect(url):
            if "expired" in url:
                return _valid_body("This job has expired. ")
            return _valid_body("Great opportunity! Apply now. ")

        agent = _agent(side_effect=fetch_side_effect)
        state = _make_state("job", [
            "https://example.com/expired-job",
            "https://example.com/good-job",
        ])
        result = await agent(state)

        assert len(result["raw_job_results"]) == 1
        assert result["raw_job_results"][0]["url"] == "https://example.com/good-job"
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is True

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
        assert result["url_validation_results"][0]["valid"] is True

    @pytest.mark.asyncio
    async def test_no_fetch_tool_returns_empty(self):
        agent = URLValidatorAgent()
        state = _make_state("job", ["https://example.com/job1"])
        result = await agent(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_linkedin_generic_page_flagged_invalid(self):
        """LinkedIn page without actual-page markers is flagged as generic."""
        body = _valid_body("Senior Dev at BigCo. report this job. about the role. ")
        agent = _agent(return_value=body)
        state = _make_state("job", ["https://linkedin.com/jobs/view/12345"])
        result = await agent(state)

        assert result["raw_job_results"] == []
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_linkedin_actual_page_passes(self):
        """LinkedIn page with actual-page markers passes validation."""
        body = _valid_body(
            "Senior Dev at BigCo. use ai to assess how you fit. "
            "sign in to evaluate your skills. Great role! "
        )
        agent = _agent(return_value=body)
        state = _make_state("job", ["https://linkedin.com/jobs/view/12345"])
        result = await agent(state)

        assert "raw_job_results" not in result
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is True
