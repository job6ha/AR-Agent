import asyncio

from backend.domain.kaeri_ar_agent.agents.outliner import generate_outline, generate_outline_async


class FakeLLM:
    async def astream(self, _prompt):
        yield type("Chunk", (), {"content": '{"topic":"T","outline":["A","B"]}'})


def test_generate_outline_mock():
    result = generate_outline("prompt", mock_mode=True)
    assert "outline" in result
    assert result["outline"]


def test_generate_outline_with_llm():
    result = asyncio.run(generate_outline_async("prompt", llm=FakeLLM(), mock_mode=False))
    assert result["topic"] == "T"
    assert result["outline"] == ["A", "B"]
