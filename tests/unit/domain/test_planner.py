import asyncio

from backend.domain.kaeri_ar_agent.agents.planner import build_query_plan, build_query_plan_async
from backend.domain.kaeri_ar_agent.schemas import PipelineInputs


class FakeLLM:
    async def astream(self, _prompt):
        yield type("Chunk", (), {"content": '["q1","q2"]'})


def test_build_query_plan_mock():
    inputs = PipelineInputs(topic="t", outline=["C1"])
    plan = build_query_plan(inputs, mock_mode=True)
    assert plan["C1"]


def test_build_query_plan_llm():
    inputs = PipelineInputs(topic="t", outline=["C1"])
    plan = asyncio.run(build_query_plan_async(inputs, llm=FakeLLM(), mock_mode=False))
    assert plan["C1"] == ["q1", "q2"]
