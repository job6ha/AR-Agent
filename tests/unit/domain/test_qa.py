import asyncio

from backend.domain.kaeri_ar_agent.agents.qa import qa_checks, qa_checks_async
from backend.domain.kaeri_ar_agent.schemas import DraftNode


class FakeLLM:
    async def astream(self, _prompt):
        yield type("Chunk", (), {"content": '["extra issue"]'})


def test_qa_checks_basic():
    drafts = [DraftNode(chapter_id="C1", paragraph_id="P1", text="입니다", citation_source_ids=[])]
    issues = qa_checks(drafts, llm=None)
    assert any("Honorific" in issue for issue in issues)


def test_qa_checks_with_llm():
    drafts = [DraftNode(chapter_id="C1", paragraph_id="P1", text="text", citation_source_ids=[])]
    issues = asyncio.run(qa_checks_async(drafts, llm=FakeLLM()))
    assert "extra issue" in issues
