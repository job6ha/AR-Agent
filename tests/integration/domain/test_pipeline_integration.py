from backend.domain.kaeri_ar_agent import AgentConfig, run_pipeline
from backend.domain.kaeri_ar_agent.schemas import PipelineInputs


def test_run_pipeline_mock_mode():
    config = AgentConfig(mock_mode=True)
    inputs = PipelineInputs(topic="topic", outline=["C1"])
    state = run_pipeline(config, inputs)
    assert state.get("composed_text")
    assert state.get("sources")
    assert state.get("drafts")
