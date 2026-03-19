"""End-to-end tests for the cover letter pipeline with mock agents."""

import pytest

from app.agents.factory import AgentFactory
from app.engine.audit_writer import AuditWriter
from app.engine.verifier import Verifier
from app.graphs.cover_letter import build_cover_letter_graph


@pytest.fixture()
def mock_factory():
    return AgentFactory()


class TestCoverLetterPipeline:
    @pytest.mark.asyncio
    async def test_cover_letter_pipeline_produces_content(self, mock_factory):
        graph = build_cover_letter_graph(agent_factory=mock_factory)
        compiled = graph.compile()

        result = await compiled.ainvoke({
            "profile_id": "test-profile",
            "cv_content": "Python developer with 5 years experience in FastAPI and AWS.",
            "jd_text": "Looking for a senior Python developer with cloud experience.",
            "job_opportunity": {"title": "Senior Python Developer", "company": "TechCorp"},
            "run_id": "test-run-cl",
            "errors": [],
            "audit_events": [],
        })

        assert "cover_letter_content" in result
        content = result["cover_letter_content"]
        assert len(content) > 50
        assert "Senior Python Developer" in content

    @pytest.mark.asyncio
    async def test_cover_letter_pipeline_with_audit(self, mock_factory, tmp_path):
        audit_writer = AuditWriter(artifacts_dir=tmp_path / "artifacts")
        graph = build_cover_letter_graph(
            audit_writer=audit_writer, agent_factory=mock_factory,
        )
        compiled = graph.compile()

        run_id = "test-run-cl-audit"
        await compiled.ainvoke({
            "profile_id": "test-profile",
            "cv_content": "Python dev",
            "jd_text": "Senior developer role",
            "job_opportunity": {"title": "SWE"},
            "run_id": run_id,
            "errors": [],
            "audit_events": [],
        })

        bundle = await audit_writer.read_bundle(run_id)
        assert bundle is not None
        assert "cover_letter" in bundle["final_artifacts"]

    @pytest.mark.asyncio
    async def test_cover_letter_pipeline_with_verifier(self, mock_factory, tmp_path):
        audit_writer = AuditWriter(artifacts_dir=tmp_path / "artifacts")
        verifier = Verifier()
        graph = build_cover_letter_graph(
            audit_writer=audit_writer,
            agent_factory=mock_factory,
            verifier=verifier,
        )
        compiled = graph.compile()

        run_id = "test-run-cl-verified"
        result = await compiled.ainvoke({
            "profile_id": "test-profile",
            "cv_content": "Python developer with 5 years experience.",
            "jd_text": "Looking for senior developer.",
            "job_opportunity": {"title": "Senior Dev", "company": "Corp"},
            "run_id": run_id,
            "errors": [],
            "audit_events": [],
        })

        # Verifier results should include cover_letter_agent
        assert "verifier_results" in result
        agent_names = [vr["agent_name"] for vr in result["verifier_results"]]
        assert "cover_letter_agent" in agent_names

        for vr in result["verifier_results"]:
            assert vr["status"] == "pass", (
                f"Agent {vr['agent_name']} verification failed: {vr}"
            )

        # Audit bundle should have real verifier report
        bundle = await audit_writer.read_bundle(run_id)
        assert bundle is not None
        report = bundle["verifier_report"]
        assert report != {}
        assert report["overall_status"] == "pass"
        assert report["failures"] == 0
