"""End-to-end tests for the weekly pipeline with mock agents."""

import pytest

from app.agents.factory import AgentFactory
from app.engine.audit_writer import AuditWriter
from app.engine.verifier import Verifier
from app.graphs.weekly import build_weekly_graph


@pytest.fixture()
def mock_factory():
    return AgentFactory()


class TestWeeklyPipeline:
    @pytest.mark.asyncio
    async def test_weekly_pipeline_produces_results_with_ceo_cfo(self, mock_factory):
        graph = build_weekly_graph(agent_factory=mock_factory)
        compiled = graph.compile()

        result = await compiled.ainvoke({
            "profile_id": "test-profile",
            "profile_targets": ["cloud", "devops"],
            "profile_skills": ["python", "aws"],
            "run_id": "test-run-weekly",
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })

        # Should have all daily results
        assert "formatted_jobs" in result
        assert "formatted_certifications" in result
        assert "formatted_trends" in result

        # Plus CEO/CFO outputs
        assert "strategic_recommendations" in result
        assert "ceo_summary" in result
        assert "risk_assessments" in result
        assert "cfo_summary" in result

        assert len(result["strategic_recommendations"]) > 0
        assert len(result["risk_assessments"]) > 0

    @pytest.mark.asyncio
    async def test_weekly_pipeline_no_errors(self, mock_factory):
        graph = build_weekly_graph(agent_factory=mock_factory)
        compiled = graph.compile()

        result = await compiled.ainvoke({
            "profile_id": "test-profile",
            "profile_targets": ["python"],
            "profile_skills": [],
            "run_id": "test-run-weekly-2",
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })

        assert result.get("errors", []) == []

    @pytest.mark.asyncio
    async def test_weekly_pipeline_with_audit(self, mock_factory, tmp_path):
        audit_writer = AuditWriter(artifacts_dir=tmp_path / "artifacts")
        graph = build_weekly_graph(
            audit_writer=audit_writer, agent_factory=mock_factory,
        )
        compiled = graph.compile()

        run_id = "test-run-weekly-audit"
        await compiled.ainvoke({
            "profile_id": "test-profile",
            "profile_targets": ["python"],
            "profile_skills": [],
            "run_id": run_id,
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })

        bundle = await audit_writer.read_bundle(run_id)
        assert bundle is not None
        assert "jobs" in bundle["final_artifacts"]
        assert "strategic_recommendations" in bundle["final_artifacts"]
        assert "risk_assessments" in bundle["final_artifacts"]

    @pytest.mark.asyncio
    async def test_weekly_pipeline_with_verifier(self, mock_factory, tmp_path):
        audit_writer = AuditWriter(artifacts_dir=tmp_path / "artifacts")
        verifier = Verifier()
        graph = build_weekly_graph(
            audit_writer=audit_writer,
            agent_factory=mock_factory,
            verifier=verifier,
        )
        compiled = graph.compile()

        run_id = "test-run-weekly-verified"
        result = await compiled.ainvoke({
            "profile_id": "test-profile",
            "profile_targets": ["cloud", "devops"],
            "profile_skills": ["python"],
            "run_id": run_id,
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })

        # Verifier results should include goal_extractor, web_scrapers,
        # data_formatter, ceo, cfo
        assert "verifier_results" in result
        agent_names = [vr["agent_name"] for vr in result["verifier_results"]]
        assert "goal_extractor" in agent_names
        assert "web_scrapers" in agent_names
        assert "data_formatter" in agent_names
        assert "ceo" in agent_names
        assert "cfo" in agent_names

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
