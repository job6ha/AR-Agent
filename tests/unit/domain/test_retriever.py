from backend.domain.kaeri_ar_agent.agents.retriever import _cosine_similarity, retrieve_sources
from backend.domain.kaeri_ar_agent.config import AgentConfig


def test_cosine_similarity():
    assert _cosine_similarity([1, 0], [1, 0]) == 1.0
    assert _cosine_similarity([1, 0], [0, 1]) == 0.0


def test_retrieve_sources_mock_mode():
    config = AgentConfig(mock_mode=True)
    sources = retrieve_sources(config, {"C1": ["query"]})
    assert sources
