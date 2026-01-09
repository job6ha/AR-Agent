import asyncio

from backend.domain.kaeri_ar_agent.llm_stream import stream_llm_response


class FakeChunk:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    async def astream(self, _prompt):
        for part in ["Hello", " ", "world"]:
            yield FakeChunk(part)


def test_stream_llm_response_collects_chunks():
    events = []

    def emit(agent, message, payload):
        events.append((agent, message, payload))

    text = asyncio.run(stream_llm_response(FakeLLM(), "Prompt", emit, "tester"))
    assert text == "Hello world"
    assert any(event[1] == "llm stream started" for event in events)
    assert any(event[1] == "llm stream completed" for event in events)
