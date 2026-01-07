from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the agent pipeline."""

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_embedding_model: str = "text-embedding-3-small"
    planner_model: Optional[str] = None
    planner_temperature: Optional[float] = None
    outliner_model: Optional[str] = None
    outliner_temperature: Optional[float] = None
    retriever_model: Optional[str] = None
    retriever_temperature: Optional[float] = None
    extractor_model: Optional[str] = None
    extractor_temperature: Optional[float] = None
    writer_model: Optional[str] = None
    writer_temperature: Optional[float] = None
    composer_model: Optional[str] = None
    composer_temperature: Optional[float] = None
    auditor_model: Optional[str] = None
    auditor_temperature: Optional[float] = None
    qa_model: Optional[str] = None
    qa_temperature: Optional[float] = None
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    request_timeout_s: float = 20.0
    request_retry_count: int = 2
    request_retry_backoff_s: float = 1.0
    mock_mode: bool = True
    max_sources: int = 20
    max_evidence_per_chapter: int = 12
    max_queries_per_chapter: int = 3
    max_query_length: int = 200
    max_iterations: int = 2
    max_concurrency: int = 6
    prompts_path: str = "backend/prompts.yaml"
    g2_mode: str = "hard"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            planner_model=os.getenv("PLANNER_MODEL"),
            planner_temperature=_float_or_none(os.getenv("PLANNER_TEMPERATURE")),
            outliner_model=os.getenv("OUTLINER_MODEL"),
            outliner_temperature=_float_or_none(os.getenv("OUTLINER_TEMPERATURE")),
            retriever_model=os.getenv("RETRIEVER_MODEL"),
            retriever_temperature=_float_or_none(os.getenv("RETRIEVER_TEMPERATURE")),
            extractor_model=os.getenv("EXTRACTOR_MODEL"),
            extractor_temperature=_float_or_none(os.getenv("EXTRACTOR_TEMPERATURE")),
            writer_model=os.getenv("WRITER_MODEL"),
            writer_temperature=_float_or_none(os.getenv("WRITER_TEMPERATURE")),
            composer_model=os.getenv("COMPOSER_MODEL"),
            composer_temperature=_float_or_none(os.getenv("COMPOSER_TEMPERATURE")),
            auditor_model=os.getenv("AUDITOR_MODEL"),
            auditor_temperature=_float_or_none(os.getenv("AUDITOR_TEMPERATURE")),
            qa_model=os.getenv("QA_MODEL"),
            qa_temperature=_float_or_none(os.getenv("QA_TEMPERATURE")),
            arxiv_base_url=os.getenv("ARXIV_BASE_URL", "https://export.arxiv.org/api/query"),
            request_timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", "20")),
            request_retry_count=int(os.getenv("REQUEST_RETRY_COUNT", "2")),
            request_retry_backoff_s=float(os.getenv("REQUEST_RETRY_BACKOFF_S", "1.0")),
            mock_mode=os.getenv("MOCK_MODE", "true").lower() == "true",
            max_sources=int(os.getenv("MAX_SOURCES", "20")),
            max_evidence_per_chapter=int(os.getenv("MAX_EVIDENCE_PER_CHAPTER", "12")),
            max_queries_per_chapter=int(os.getenv("MAX_QUERIES_PER_CHAPTER", "3")),
            max_query_length=int(os.getenv("MAX_QUERY_LENGTH", "200")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "2")),
            max_concurrency=int(os.getenv("MAX_CONCURRENCY", "6")),
            prompts_path=os.getenv("PROMPTS_PATH", "backend/prompts.yaml"),
            g2_mode=os.getenv("G2_MODE", "hard"),
        )

    def build_llm(self, agent: Optional[str] = None) -> ChatOpenAI:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when mock_mode is false.")
        model = self.openai_model
        temperature = self.openai_temperature
        if agent == "planner":
            model = self.planner_model or model
            temperature = self.planner_temperature or temperature
        elif agent == "outliner":
            model = self.outliner_model or model
            temperature = self.outliner_temperature or temperature
        elif agent == "retriever":
            model = self.retriever_model or model
            temperature = self.retriever_temperature or temperature
        elif agent == "extractor":
            model = self.extractor_model or model
            temperature = self.extractor_temperature or temperature
        elif agent == "writer":
            model = self.writer_model or model
            temperature = self.writer_temperature or temperature
        elif agent == "composer":
            model = self.composer_model or model
            temperature = self.composer_temperature or temperature
        elif agent == "auditor":
            model = self.auditor_model or model
            temperature = self.auditor_temperature or temperature
        elif agent == "qa":
            model = self.qa_model or model
            temperature = self.qa_temperature or temperature
        return ChatOpenAI(
            model=model,
            temperature=_normalize_temperature(model, temperature),
            api_key=self.openai_api_key,
            streaming=True,
        )

    def build_embeddings(self) -> OpenAIEmbeddings:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when mock_mode is false.")
        return OpenAIEmbeddings(
            model=self.openai_embedding_model,
            api_key=self.openai_api_key,
        )

    def agent_settings(self, agent: str) -> dict:
        model = self.openai_model
        temperature = self.openai_temperature
        if agent == "planner":
            model = self.planner_model or model
            temperature = self.planner_temperature or temperature
        elif agent == "retriever":
            model = self.retriever_model or model
            temperature = self.retriever_temperature or temperature
        elif agent == "extractor":
            model = self.extractor_model or model
            temperature = self.extractor_temperature or temperature
        elif agent == "writer":
            model = self.writer_model or model
            temperature = self.writer_temperature or temperature
        elif agent == "composer":
            model = self.composer_model or model
            temperature = self.composer_temperature or temperature
        elif agent == "auditor":
            model = self.auditor_model or model
            temperature = self.auditor_temperature or temperature
        elif agent == "qa":
            model = self.qa_model or model
            temperature = self.qa_temperature or temperature
        return {"model": model, "temperature": temperature}


def _float_or_none(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def _normalize_temperature(model: str, temperature: Optional[float]) -> float:
    if temperature is None:
        return 1.0
    lowered = model.lower()
    if lowered.startswith("o3") or lowered.startswith("gpt-5"):
        return 1.0
    return temperature
