from backend.domain.kaeri_ar_agent.agents.refiner import refine_query_plan
from backend.domain.kaeri_ar_agent.schemas import PipelineInputs


def test_refiner_adds_resolution_queries():
    inputs = PipelineInputs(topic="t", outline=["C1"])
    plan = {"C1": ["q1"]}
    refined = refine_query_plan(inputs, plan, ["Consensus pending for 1 sources."], mock_mode=True)
    assert any("DOI" in q for q in refined["C1"])
