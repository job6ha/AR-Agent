import os

import pytest

from backend.domain.kaeri_ar_agent.config import (
    AgentConfig,
    _float_or_none,
    _normalize_temperature,
)


def test_float_or_none():
    assert _float_or_none(None) is None
    assert _float_or_none("") is None
    assert _float_or_none("1.5") == 1.5


def test_normalize_temperature_for_o3_and_gpt5():
    assert _normalize_temperature("o3-mini", 0.2) == 1.0
    assert _normalize_temperature("gpt-5-mini", 0.2) == 1.0
    assert _normalize_temperature("gpt-4o-mini", 0.2) == 0.2


def test_agent_settings_defaults():
    config = AgentConfig(openai_model="model-a", openai_temperature=0.3)
    settings = config.agent_settings("planner")
    assert settings["model"] == "model-a"
    assert settings["temperature"] == 0.3


def test_from_env_reads_custom_values(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "model-b")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.4")
    monkeypatch.setenv("PROVIDER_TIMEOUT_S", "12")
    monkeypatch.setenv("VERIFY_MODE", "soft")
    config = AgentConfig.from_env()
    assert config.openai_model == "model-b"
    assert config.openai_temperature == 0.4
    assert config.provider_timeout_s == 12.0
    assert config.verify_mode == "soft"


def test_build_llm_requires_api_key():
    config = AgentConfig(openai_api_key=None, mock_mode=False)
    with pytest.raises(ValueError):
        config.build_llm("planner")


def test_build_embeddings_requires_api_key():
    config = AgentConfig(openai_api_key=None, mock_mode=False)
    with pytest.raises(ValueError):
        config.build_embeddings()
