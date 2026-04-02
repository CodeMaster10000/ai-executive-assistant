"""Tests for the post-scraper link validator."""

import asyncio

import httpx
import pytest

from app.engine.link_validator import LinkValidator


def _mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok_handler(request):
    return httpx.Response(200, text="<html>Apply now</html>")


def _validator(http_client=None, **overrides):
    config = {"enabled": True, **overrides}
    return LinkValidator(config=config, http_client=http_client)


def _job(title, url):
    return {"title": title, "url": url, "source": "Test"}


# ------------------------------------------------------------------
# URL pattern filtering (liveness disabled)
# ------------------------------------------------------------------


class TestPatternFiltering:

    @pytest.mark.asyncio
    async def test_search_page_urls_removed(self):
        v = LinkValidator()
        results = [
            _job("Python jobs", "https://indeed.com/jobs?q=python&l=remote"),
            _job("Dev roles", "https://glassdoor.com/Job/results.htm?sc.keyword=developer"),
            _job("Search results", "https://linkedin.com/jobs/search?keywords=python"),
            _job("Find jobs", "https://example.com/find?query=backend"),
        ]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 0
        assert len(removed) == 4

    @pytest.mark.asyncio
    async def test_valid_posting_urls_kept(self):
        v = LinkValidator()
        results = [
            _job("Senior Dev", "https://linkedin.com/jobs/view/123456789"),
            _job("Backend Engineer", "https://indeed.com/viewjob?jk=abc123def456"),
            _job("Full Stack Dev", "https://glassdoor.com/job-listing/full-stack-JL12345.htm"),
            _job("Python Role", "https://teal.com/job/senior-python-dev-12345"),
        ]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 4
        assert len(removed) == 0

    @pytest.mark.asyncio
    async def test_generic_index_path_removed(self):
        v = LinkValidator()
        results = [
            _job("Jobs", "https://indeed.com/jobs"),
            _job("Jobs", "https://linkedin.com/jobs/"),
        ]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 0
        assert len(removed) == 2

    @pytest.mark.asyncio
    async def test_mixed_valid_and_invalid(self):
        v = LinkValidator()
        results = [
            _job("Real posting", "https://linkedin.com/jobs/view/999"),
            _job("Search page", "https://indeed.com/jobs?q=python"),
            _job("Another posting", "https://example.com/careers/backend-engineer-42"),
        ]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 2
        assert len(removed) == 1
        assert kept[0]["title"] == "Real posting"
        assert kept[1]["title"] == "Another posting"

    @pytest.mark.asyncio
    async def test_empty_url_removed(self):
        v = LinkValidator()
        results = [{"title": "No URL", "url": "", "source": "Unknown"}]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 0
        assert len(removed) == 1

    @pytest.mark.asyncio
    async def test_missing_url_key_removed(self):
        v = LinkValidator()
        results = [{"title": "No URL key", "source": "Unknown"}]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 0
        assert len(removed) == 1

    @pytest.mark.asyncio
    async def test_empty_input(self):
        v = LinkValidator()
        kept, removed = await v.validate_results([], "job")
        assert kept == []
        assert removed == []

    @pytest.mark.asyncio
    async def test_custom_patterns(self):
        v = LinkValidator({"search_page_patterns": [r"/custom-search"]})
        results = [
            _job("Custom", "https://example.com/custom-search"),
            _job("Normal", "https://example.com/job/123"),
        ]
        kept, removed = await v.validate_results(results, "job")
        assert len(kept) == 1
        assert len(removed) == 1
        assert kept[0]["title"] == "Normal"


class TestNonJobCategories:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("category", ["cert", "event", "group", "trend"])
    async def test_non_job_categories_pass_through(self, category):
        v = LinkValidator()
        results = [_job("Something", "https://example.com/search?q=test")]
        kept, removed = await v.validate_results(results, category)
        assert len(kept) == 1
        assert len(removed) == 0

    @pytest.mark.asyncio
    async def test_non_job_passes_through_with_liveness_enabled(self):
        v = LinkValidator(config={"enabled": True})
        results = [_job("Cert", "https://example.com/search?q=aws")]
        kept, removed = await v.validate_results(results, "cert")
        assert len(kept) == 1
        assert len(removed) == 0


# ------------------------------------------------------------------
# HTTP liveness checks
# ------------------------------------------------------------------


class TestLivenessDisabled:

    @pytest.mark.asyncio
    async def test_disabled_skips_http(self):
        called = False

        def handler(request):
            nonlocal called
            called = True
            return httpx.Response(200)

        client = _mock_client(handler)
        v = LinkValidator(config={"enabled": False}, http_client=client)

        results = [_job("A job", "https://example.com/job/1")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert not called
        await client.aclose()


class TestLivenessAlive:

    @pytest.mark.asyncio
    async def test_200_clean_body_kept(self):
        client = _mock_client(_ok_handler)
        v = _validator(client)

        results = [_job("Python Dev", "https://example.com/job/123")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert len(removed) == 0
        assert kept[0]["_liveness"]["is_alive"] is True
        assert kept[0]["_liveness"]["reason"] == "ok"
        await client.aclose()


class TestLivenessDead:

    @pytest.mark.asyncio
    async def test_404_removed(self):
        client = _mock_client(lambda r: httpx.Response(404, text="Not Found"))
        v = _validator(client)

        results = [_job("Gone Job", "https://example.com/job/999")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 0
        assert len(removed) == 1
        assert removed[0]["_liveness"]["reason"] == "dead_status_404"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_410_removed(self):
        client = _mock_client(lambda r: httpx.Response(410, text="Gone"))
        v = _validator(client)

        results = [_job("Old Job", "https://example.com/job/old")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 0
        assert len(removed) == 1
        assert removed[0]["_liveness"]["reason"] == "dead_status_410"
        await client.aclose()


class TestLivenessHead405Fallback:

    @pytest.mark.asyncio
    async def test_head_405_falls_back_to_get(self):
        def handler(request):
            if request.method == "HEAD":
                return httpx.Response(405)
            return httpx.Response(200, text="<html>Apply here</html>")

        client = _mock_client(handler)
        v = _validator(client)

        results = [_job("Fallback Job", "https://example.com/job/fb")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert kept[0]["_liveness"]["reason"] == "ok"
        await client.aclose()


class TestLivenessRedirect:

    @pytest.mark.asyncio
    async def test_redirect_to_homepage_removed(self):
        def handler(request):
            if request.url.path == "/job/old":
                return httpx.Response(301, headers={"Location": "https://example.com/jobs/"})
            return httpx.Response(200, text="<html>Job Board</html>")

        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )
        v = _validator(client)

        results = [_job("Redirected Job", "https://example.com/job/old")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 0
        assert len(removed) == 1
        assert removed[0]["_liveness"]["reason"] == "redirect_to_homepage"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_redirect_to_valid_page_kept(self):
        def handler(request):
            if request.url.path == "/job/old-slug":
                return httpx.Response(301, headers={"Location": "https://example.com/job/new-slug-123"})
            return httpx.Response(200, text="<html>Senior Dev - Apply</html>")

        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )
        v = _validator(client)

        results = [_job("Moved Job", "https://example.com/job/old-slug")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert kept[0]["_liveness"]["reason"] == "ok"
        await client.aclose()


class TestLivenessExpiredBody:

    @pytest.mark.asyncio
    async def test_expired_body_pattern_removed(self):
        client = _mock_client(
            lambda r: httpx.Response(200, text="<h1>This job is no longer available</h1>"),
        )
        v = _validator(client)

        results = [_job("Expired Job", "https://example.com/job/exp")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 0
        assert len(removed) == 1
        assert removed[0]["_liveness"]["reason"] == "expired_body_pattern"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_position_filled_removed(self):
        client = _mock_client(
            lambda r: httpx.Response(200, text="<p>Sorry, this position has been filled.</p>"),
        )
        v = _validator(client)

        results = [_job("Filled Job", "https://example.com/job/filled")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 0
        assert len(removed) == 1
        assert removed[0]["_liveness"]["reason"] == "expired_body_pattern"
        await client.aclose()


class TestLivenessNetworkErrors:

    @pytest.mark.asyncio
    async def test_connect_error_kept(self):
        client = _mock_client(lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")))
        v = _validator(client)

        results = [_job("Unreachable", "https://example.com/job/down")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert len(removed) == 0
        assert "network_error" in kept[0]["_liveness"]["reason"]
        await client.aclose()

    @pytest.mark.asyncio
    async def test_timeout_error_kept(self):
        client = _mock_client(lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("timed out")))
        v = _validator(client)

        results = [_job("Slow Job", "https://example.com/job/slow")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert len(removed) == 0
        assert "network_error" in kept[0]["_liveness"]["reason"]
        await client.aclose()


class TestLivenessMixed:

    @pytest.mark.asyncio
    async def test_mixed_alive_and_dead(self):
        def handler(request):
            if "dead" in str(request.url):
                return httpx.Response(404, text="Not Found")
            if "expired" in str(request.url):
                return httpx.Response(200, text="<html>This job has expired</html>")
            return httpx.Response(200, text="<html>Apply now!</html>")

        client = _mock_client(handler)
        v = _validator(client)

        results = [
            _job("Live Job", "https://example.com/job/live"),
            _job("Dead Job", "https://example.com/job/dead"),
            _job("Expired Job", "https://example.com/job/expired"),
            _job("Another Live", "https://example.com/job/alive"),
        ]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 2
        assert len(removed) == 2
        assert {r["title"] for r in kept} == {"Live Job", "Another Live"}
        await client.aclose()


class TestPatternPlusHttp:

    @pytest.mark.asyncio
    async def test_search_page_skips_http(self):
        http_checked_urls = []

        def handler(request):
            http_checked_urls.append(str(request.url))
            return httpx.Response(200, text="<html>OK</html>")

        client = _mock_client(handler)
        v = _validator(client)

        results = [
            _job("Search page", "https://example.com/jobs?q=python"),
            _job("Valid posting", "https://example.com/job/123"),
        ]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert len(removed) == 1
        assert removed[0]["title"] == "Search page"
        assert all("job/123" in u for u in http_checked_urls)
        await client.aclose()


class TestBatchTimeout:

    @pytest.mark.asyncio
    async def test_batch_timeout_assumes_alive(self):
        async def slow_handler(request):
            await asyncio.sleep(10)
            return httpx.Response(200, text="OK")

        client = httpx.AsyncClient(transport=httpx.MockTransport(slow_handler))
        v = _validator(client, batch_timeout_seconds=0.1)

        results = [_job("Slow Job", "https://example.com/job/slow")]
        kept, removed = await v.validate_results(results, "job")

        assert len(kept) == 1
        assert len(removed) == 0
        await client.aclose()


class TestLivenessMetadata:

    @pytest.mark.asyncio
    async def test_metadata_on_kept(self):
        client = _mock_client(_ok_handler)
        v = _validator(client)

        results = [_job("Job", "https://example.com/job/1")]
        kept, _ = await v.validate_results(results, "job")

        liveness = kept[0]["_liveness"]
        assert liveness["is_alive"] is True
        assert liveness["status_code"] == 200
        assert liveness["reason"] == "ok"
        assert "check_duration_ms" in liveness
        await client.aclose()

    @pytest.mark.asyncio
    async def test_metadata_on_removed(self):
        client = _mock_client(lambda r: httpx.Response(404, text="Not Found"))
        v = _validator(client)

        results = [_job("Dead", "https://example.com/job/gone")]
        _, removed = await v.validate_results(results, "job")

        liveness = removed[0]["_liveness"]
        assert liveness["is_alive"] is False
        assert liveness["status_code"] == 404
        assert liveness["reason"] == "dead_status_404"
        await client.aclose()
