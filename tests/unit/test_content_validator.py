"""Unit tests for the deterministic ContentValidator."""

from unittest.mock import AsyncMock

import pytest

from app.engine.content_validator import ContentValidator, _MIN_BODY_CHARS


def _valid_body(extra: str = "") -> str:
    """Return a fetch result with enough content to pass the length check."""
    filler = "Lorem ipsum dolor sit amet. " * 100
    return f"HTTP 200\n\n{extra}{filler}"


def _make_state(category: str, urls: list[str]) -> dict:
    key = f"raw_{category}_results"
    return {key: [{"url": u, "title": f"Item {i}"} for i, u in enumerate(urls)]}


def _validator(side_effect=None, return_value=None) -> ContentValidator:
    fetch_tool = AsyncMock()
    if side_effect is not None:
        fetch_tool.ainvoke.side_effect = side_effect
    elif return_value is not None:
        fetch_tool.ainvoke.return_value = return_value
    return ContentValidator(fetch_tool=fetch_tool)


class TestDeterministicPrepass:
    @pytest.mark.asyncio
    async def test_catches_expired_job(self):
        v = _validator(return_value=_valid_body(
            "This position is closed. No longer accepting applications. "
        ))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/111"])
        result = await v(state)

        assert result["raw_job_results"] == []
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert result["url_validation_results"][0]["reason"] != ""

    @pytest.mark.asyncio
    async def test_catches_ended_event(self):
        v = _validator(return_value=_valid_body("This event has ended. "))
        state = _make_state("event", ["https://example.com/event1"])
        result = await v(state)

        assert result["raw_event_results"] == []

    @pytest.mark.asyncio
    async def test_catches_retired_cert(self):
        v = _validator(return_value=_valid_body(
            "This certification has been discontinued. "
        ))
        state = _make_state("cert", ["https://example.com/cert1"])
        result = await v(state)

        assert result["raw_cert_results"] == []

    @pytest.mark.asyncio
    async def test_passes_valid_job(self):
        v = _validator(return_value=_valid_body(
            "use ai to assess how you fit. Senior Python Developer - Apply Now! "
        ))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/222"])
        result = await v(state)

        assert "raw_job_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_catches_404(self):
        v = _validator(return_value="HTTP 404\n\nPage not found")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/333"])
        result = await v(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_catches_fetch_error(self):
        v = _validator(return_value="Fetch error: Connection timed out")
        state = _make_state("trend", ["https://example.com/broken"])
        result = await v(state)

        assert result["raw_trend_results"] == []

    @pytest.mark.asyncio
    async def test_catches_exception_in_gather(self):
        v = _validator(side_effect=RuntimeError("network down"))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/444"])
        result = await v(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_catches_short_content(self):
        v = _validator(return_value="HTTP 200\n\nShort page.")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/555"])
        result = await v(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        v = _validator(return_value=_valid_body("NO LONGER ACCEPTING APPLICATIONS "))
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/666"])
        result = await v(state)

        assert result["raw_job_results"] == []

    @pytest.mark.asyncio
    async def test_filters_only_invalid_urls(self):
        async def fetch_side_effect(url):
            if "777" in url:
                return _valid_body("This job has expired. ")
            return _valid_body("use ai to assess how you fit. Great opportunity! ")

        v = _validator(side_effect=fetch_side_effect)
        state = _make_state("job", [
            "https://www.linkedin.com/jobs/view/777",
            "https://www.linkedin.com/jobs/view/888",
        ])
        result = await v(state)

        assert len(result["raw_job_results"]) == 1
        assert result["raw_job_results"][0]["url"] == "https://www.linkedin.com/jobs/view/888"
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert result["url_validation_results"][0]["reason"] != ""

    @pytest.mark.asyncio
    async def test_empty_state_returns_empty(self):
        v = _validator(return_value="")
        result = await v({})
        assert result == {}

    @pytest.mark.asyncio
    async def test_body_at_exact_threshold_is_valid(self):
        body = "x" * _MIN_BODY_CHARS
        v = _validator(return_value=f"HTTP 200\n\n{body}")
        state = _make_state("trend", ["https://example.com/trend"])
        result = await v(state)

        assert "raw_trend_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_no_fetch_tool_returns_empty(self):
        v = ContentValidator()
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/999"])
        result = await v(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_linkedin_slug_url_passes(self):
        """LinkedIn URL with slug before numeric ID passes validation."""
        body = _valid_body("Senior Dev at BigCo. Great role! Apply now. ")
        v = _validator(return_value=body)
        state = _make_state("job", [
            "https://www.linkedin.com/jobs/view/senior-dev-at-bigco-4390698710",
        ])
        result = await v(state)

        assert "raw_job_results" not in result
        assert result["url_validation_results"] == []

    @pytest.mark.asyncio
    async def test_invalid_results_include_reason(self):
        """Invalid URLs appear in url_validation_results with reason."""
        v = _validator(return_value="HTTP 404\n\nPage not found")
        state = _make_state("job", ["https://www.linkedin.com/jobs/view/12345"])
        result = await v(state)

        assert result["raw_job_results"] == []
        assert len(result["url_validation_results"]) == 1
        assert result["url_validation_results"][0]["valid"] is False
        assert "404" in result["url_validation_results"][0]["reason"]
