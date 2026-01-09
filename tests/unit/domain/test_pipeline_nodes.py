from backend.domain.kaeri_ar_agent.pipeline import (
    _audit_node,
    _compose_node,
    _extract_node,
    _gate_evidence_node,
    _gate_g1_node,
    _gate_g1a_node,
    _init_state,
    _outline_node,
    _plan_node,
    _qa_node,
    _refine_node,
    _resolve_node,
    _retrieve_node,
    _status_node,
    _write_node,
)
from backend.domain.kaeri_ar_agent.config import AgentConfig
from backend.domain.kaeri_ar_agent.schemas import PipelineInputs


def test_pipeline_nodes_mock_flow():
    config = AgentConfig(mock_mode=True)
    inputs = PipelineInputs(topic="topic", outline=["C1"])
    state = _init_state(inputs, config)
    state.update(_outline_node(state, config, emit=None))
    state.update(_plan_node(state, config, emit=None))
    state.update(_retrieve_node(state, config, emit=None))
    state.update(_gate_g1_node(state, emit=None))
    state.update(_resolve_node(state, config, emit=None))
    state.update(_gate_g1a_node(state, config, emit=None))
    state.update(_status_node(state, config, emit=None))
    state.update(_extract_node(state, config, emit=None))
    state.update(_gate_evidence_node(state, emit=None))
    state.update(_write_node(state, config, emit=None))
    state.update(_audit_node(state, config, emit=None))
    state.update(_compose_node(state, config, emit=None))
    state.update(_qa_node(state, config, emit=None))
    state.update(_refine_node(state, config, emit=None))
    assert state.get("composed_text") is not None
