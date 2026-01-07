from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import re

from langgraph.graph import END, StateGraph

from .agents.auditor import audit_citations
from .agents.composer import compose_text
from .agents.extractor import extract_evidence
from .agents.outliner import generate_outline
from .agents.planner import build_query_plan
from .agents.qa import qa_checks
from .agents.retriever import retrieve_sources
from .agents.refiner import refine_query_plan
from .agents.writer import write_chapters
from .config import AgentConfig
from .gates import gate_g1_sources
from .prompts import load_prompts
from .schemas import PipelineInputs
from .state import PipelineState


def _init_state(inputs: PipelineInputs, config: AgentConfig) -> PipelineState:
    return {
        "inputs": inputs,
        "gates": {},
        "errors": [],
        "warnings": [],
        "iteration": 0,
        "max_iterations": config.max_iterations,
        "last_issues": [],
        "prompts": load_prompts(config.prompts_path),
        "g2_route": None,
        "qa_route": None,
        "retrieval_stats": {},
        "evidence_stats": {},
    }


def _outline_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    llm = config.build_llm("outliner") if not config.mock_mode else None
    prompts = state.get("prompts", {})
    if emit:
        emit(
            "outliner",
            "outline generation started",
            {"summary": "사용자 프롬프트에서 목차를 생성하는 중"},
        )
    payload = generate_outline(
        state["inputs"].raw_prompt or state["inputs"].topic,
        llm=llm,
        mock_mode=config.mock_mode,
        emit=emit,
        system_prompt=prompts.get("outliner", ""),
    )
    inputs = PipelineInputs(
        raw_prompt=state["inputs"].raw_prompt,
        topic=str(payload.get("topic") or state["inputs"].topic),
        outline=list(payload.get("outline") or []),
        scope=payload.get("scope"),
        exclusions=list(payload.get("exclusions") or []),
    )
    errors = list(state.get("errors", []))
    if not inputs.outline:
        errors.append("Outline generation failed; no chapters returned from the LLM.")
    if emit:
        emit(
            "outliner",
            "outline generation completed",
            {
                "summary": "프롬프트 기반 목차 생성 완료",
                "topic": inputs.topic,
                "outline": inputs.outline,
                "scope": inputs.scope,
                "exclusions": inputs.exclusions,
            },
        )
    return {"inputs": inputs, "errors": errors}


def _plan_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "planner",
            "query plan generation started",
            {
                "summary": "요구 범위와 챕터를 기준으로 검색 쿼리를 설계하는 중",
                "inputs": state["inputs"].model_dump(),
                "settings": config.agent_settings("planner"),
            },
        )
    inputs = state["inputs"]
    prompts = state.get("prompts", {})
    llm = config.build_llm("planner") if not config.mock_mode else None
    result = {
        "plan_queries": build_query_plan(
            inputs,
            llm=llm,
            mock_mode=config.mock_mode,
            emit=emit,
            system_prompt=prompts.get("planner", ""),
        )
    }
    if emit:
        emit(
            "planner",
            "query plan generation completed",
            {
                "summary": "챕터별 검색 쿼리 초안을 생성함",
                "plan_queries": result["plan_queries"],
            },
        )
    return result


def _retrieve_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "retriever",
            "source retrieval started",
            {
                "summary": "검색 쿼리를 사용해 출처 후보를 수집하는 중",
                "settings": config.agent_settings("retriever"),
                "queries": state.get("plan_queries", {}),
            },
        )
    llm = config.build_llm("retriever") if not config.mock_mode else None
    plan_queries = state["plan_queries"]
    sources = retrieve_sources(config, plan_queries, llm=llm, emit=emit)
    total_queries = sum(len(queries) for queries in plan_queries.values())
    retrieval_stats = {
        "total_queries": total_queries,
        "retrieved_sources": len(sources),
    }
    if emit:
        emit(
            "retriever",
            f"source retrieval completed ({len(sources)} sources)",
            {
                "summary": "출처 후보를 수집하고 샘플을 정리함",
                "source_sample": [
                    {"source_id": source.source_id, "title": source.title}
                    for source in sources[:5]
                ]
            },
        )
    return {"sources": sources, "retrieval_stats": retrieval_stats}


def _gate_g1_node(
    state: PipelineState,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit("gates", "G1 source validation started", {"summary": "출처 무결성(doi/url, 1차 출처) 검증 중"})
    audit = gate_g1_sources(state.get("sources", []))
    last_issues: List[str] = []
    gates = {**state.get("gates", {}), "g1_passed": audit.passed}
    errors = list(state.get("errors", []))
    if not audit.passed:
        errors.extend(audit.issues)
        if emit:
            emit("gates", "G1 failed", {"summary": "출처 요건 미달로 재수집 필요", "issues": audit.issues})
        last_issues = audit.issues
    elif emit:
        emit("gates", "G1 passed", {"summary": "출처 요건 충족, 다음 단계 진행"})
    return {"gates": gates, "errors": errors, "last_issues": last_issues if not audit.passed else []}


def _extract_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "extractor",
            "evidence extraction started",
            {
                "summary": "출처에서 근거 스니펫을 추출하는 중",
                "settings": config.agent_settings("extractor"),
            },
        )
    inputs = state["inputs"]
    prompts = state.get("prompts", {})
    llm = config.build_llm("extractor") if not config.mock_mode else None
    evidence = extract_evidence(
        config,
        state.get("sources", []),
        inputs.outline,
        llm=llm,
        emit=emit,
        system_prompt=prompts.get("extractor", ""),
    )
    evidence_stats = {
        "evidence_items": len(evidence),
    }
    if emit:
        emit(
            "extractor",
            f"evidence extraction completed ({len(evidence)} items)",
            {
                "summary": "근거 스니펫 추출 완료",
                "evidence_sample": [
                    {"claim_id": item.claim_id, "source_id": item.source_id, "snippet": item.snippet[:120]}
                    for item in evidence[:5]
                ]
            },
        )
    return {"evidence": evidence, "evidence_stats": evidence_stats}


def _gate_evidence_node(
    state: PipelineState,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    outline = state["inputs"].outline
    evidence = state.get("evidence", [])
    evidence_by_chapter: Dict[str, int] = {chapter: 0 for chapter in outline}
    for item in evidence:
        if item.chapter_id in evidence_by_chapter:
            evidence_by_chapter[item.chapter_id] += 1
    missing = [chapter for chapter, count in evidence_by_chapter.items() if count == 0]
    issues = [f"No usable evidence for chapter: {chapter}" for chapter in missing]
    if emit:
        emit(
            "gates",
            "G1b evidence validation",
            {
                "summary": "챕터별 증거 유효성 점검",
                "missing_chapters": missing,
            }
            if missing
            else {"summary": "모든 챕터에 증거가 존재함"},
        )
    errors = list(state.get("errors", []))
    errors.extend(issues)
    return {"errors": errors, "last_issues": issues}


def _write_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "writer",
            "chapter drafting started",
            {
                "summary": "근거 기반으로 챕터 본문을 작성하는 중",
                "settings": config.agent_settings("writer"),
            },
        )
    inputs = state["inputs"]
    prompts = state.get("prompts", {})
    llm = config.build_llm("writer") if not config.mock_mode else None
    drafts = write_chapters(
        config,
        inputs.topic,
        inputs.scope,
        inputs.exclusions,
        inputs.outline,
        state.get("evidence", []),
        llm=llm,
        emit=emit,
        system_prompt=prompts.get("writer", ""),
    )
    if emit:
        emit(
            "writer",
            f"chapter drafting completed ({len(drafts)} sections)",
            {
                "summary": "챕터 초안 작성 완료",
                "draft_sample": [
                    {"chapter_id": draft.chapter_id, "text": draft.text[:140]}
                    for draft in drafts[:3]
                ]
            },
        )
    return {"drafts": drafts}


def _audit_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "auditor",
            "citation audit started",
            {
                "summary": "본문 인용과 출처 매핑을 검증하는 중",
                "settings": config.agent_settings("auditor"),
            },
        )
    llm = config.build_llm("auditor") if not config.mock_mode else None
    prompts = state.get("prompts", {})
    audit = audit_citations(
        state.get("sources", []),
        state.get("drafts", []),
        llm=llm,
        emit=emit,
        system_prompt=prompts.get("auditor", ""),
    )
    last_issues: List[str] = []
    gates = {**state.get("gates", {}), "g2_passed": audit.passed}
    errors = list(state.get("errors", []))
    warnings = list(state.get("warnings", []))
    g2_route = None
    iteration = state.get("iteration", 0)
    if not audit.passed:
        if config.g2_mode == "soft":
            warnings.extend(audit.issues)
            gates["g2_passed"] = True
            if emit:
                emit(
                    "auditor",
                    "G2 soft warning",
                    {"summary": "인용/출처 경고(soft gate)", "issues": audit.issues},
                )
        else:
            errors.extend(audit.issues)
            if emit:
                emit("auditor", "G2 failed", {"summary": "인용/출처 불일치 발견", "issues": audit.issues})
            g2_route = _classify_g2_route(audit.issues)
        last_issues = audit.issues
        iteration = iteration + 1
    elif emit:
        emit("auditor", "G2 passed", {"summary": "인용/출처 매핑 통과"})
    return {
        "audit": audit,
        "gates": gates,
        "errors": errors,
        "warnings": warnings,
        "last_issues": last_issues if not audit.passed else [],
        "g2_route": g2_route,
        "iteration": iteration,
    }


def _compose_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "composer",
            "composition started",
            {
                "summary": "초록과 본문을 결합해 문서 형태로 구성하는 중",
                "settings": config.agent_settings("composer"),
            },
        )
    llm = config.build_llm("composer") if not config.mock_mode else None
    prompts = state.get("prompts", {})
    sources = [source.model_dump() for source in state.get("sources", [])]
    composed = compose_text(
        state.get("drafts", []),
        sources,
        plan_queries=state.get("plan_queries"),
        scope=state["inputs"].scope,
        exclusions=state["inputs"].exclusions,
        retrieval_stats=state.get("retrieval_stats"),
        evidence_stats=state.get("evidence_stats"),
        llm=llm,
        emit=emit,
        system_prompt=prompts.get("composer", ""),
    )
    if emit:
        emit("composer", "composition completed", {"summary": "문서 구성 완료", "length": len(composed)})
    return {"composed_text": composed}


def _qa_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    if emit:
        emit(
            "qa",
            "final QA started",
            {
                "summary": "문체/구성/금지 규칙 QA 점검 중",
                "settings": config.agent_settings("qa"),
            },
        )
    llm = config.build_llm("qa") if not config.mock_mode else None
    prompts = state.get("prompts", {})
    issues = qa_checks(
        state.get("drafts", []),
        llm=llm,
        emit=emit,
        system_prompt=prompts.get("qa", ""),
        context=f"Topic: {state['inputs'].topic}; Scope: {state['inputs'].scope or ''}; Exclusions: {', '.join(state['inputs'].exclusions)}",
    )
    last_issues: List[str] = []
    qa_route = None
    errors = list(state.get("errors", []))
    if issues:
        errors.extend(issues)
        if emit:
            emit("qa", "QA issues found", {"summary": "QA 문제 발견", "issues": issues})
        last_issues = issues
        qa_route = _classify_qa_route(issues)
        iteration = state.get("iteration", 0) + 1
    elif emit:
        emit("qa", "QA passed", {"summary": "QA 통과"})
    return {
        "errors": errors,
        "last_issues": last_issues if issues else [],
        "qa_route": qa_route,
        "iteration": iteration if issues else state.get("iteration", 0),
    }


def _refine_node(
    state: PipelineState,
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]],
) -> Dict:
    iteration = state.get("iteration", 0) + 1
    inputs = state["inputs"]
    llm = config.build_llm("planner") if not config.mock_mode else None
    prompts = state.get("prompts", {})
    refined = refine_query_plan(
        inputs,
        state.get("plan_queries", {}),
        state.get("last_issues", []),
        llm=llm,
        mock_mode=config.mock_mode,
        emit=emit,
        system_prompt=prompts.get("refiner", ""),
    )
    if emit:
        emit(
            "refiner",
            f"refinement iteration {iteration}",
            {
                "summary": "검증 실패 원인을 반영해 쿼리를 재작성함",
                "issues": state.get("last_issues", []),
                "plan_queries": refined,
            },
        )
    return {"plan_queries": refined, "iteration": iteration}


def _normalize_citations_node(state: PipelineState) -> Dict:
    drafts = state.get("drafts", [])
    normalized = []
    pattern = re.compile(r"S-ARXIV-([0-9.]+v\d+)", re.IGNORECASE)
    for draft in drafts:
        text = pattern.sub(r"arXiv:\1", draft.text)
        normalized.append(
            draft.model_copy(update={"text": text})
        )
    return {"drafts": normalized}


def _classify_g2_route(issues: List[str]) -> str:
    joined = " ".join(issues).lower()
    format_signals = ["non-standard", "format", "placeholder", "s-arxiv", "bibliographic", "authors", "titles"]
    if any(signal in joined for signal in format_signals):
        return "normalize"
    return "refine"


def _classify_qa_route(issues: List[str]) -> str:
    joined = " ".join(issues)
    if any(key in joined for key in ["주제", "일관성", "스코프", "범위"]):
        return "outline"
    if any(key in joined for key in ["요약", "키워드", "참고문헌", "구조", "섹션"]):
        return "compose"
    if any(key in joined for key in ["문체", "존칭"]):
        return "write"
    if any(key in joined for key in ["재현", "방법론", "출처", "근거"]):
        return "refine"
    return "write"


def build_pipeline(
    config: AgentConfig,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None,
) -> StateGraph:
    graph = StateGraph(PipelineState)
    graph.add_node("outline", lambda state: _outline_node(state, config, emit))
    graph.add_node("plan", lambda state: _plan_node(state, config, emit))
    graph.add_node("retrieve", lambda state: _retrieve_node(state, config, emit))
    graph.add_node("gate_g1", lambda state: _gate_g1_node(state, emit))
    graph.add_node("extract", lambda state: _extract_node(state, config, emit))
    graph.add_node("gate_evidence", lambda state: _gate_evidence_node(state, emit))
    graph.add_node("write", lambda state: _write_node(state, config, emit))
    graph.add_node("audit", lambda state: _audit_node(state, config, emit))
    graph.add_node("compose", lambda state: _compose_node(state, config, emit))
    graph.add_node("qa", lambda state: _qa_node(state, config, emit))
    graph.add_node("refine", lambda state: _refine_node(state, config, emit))
    graph.add_node("normalize_citations", _normalize_citations_node)

    graph.set_entry_point("outline")
    graph.add_edge("outline", "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "gate_g1")
    graph.add_conditional_edges(
        "gate_g1",
        lambda state: "extract"
        if state.get("gates", {}).get("g1_passed")
        else ("refine" if state.get("iteration", 0) < state.get("max_iterations", 0) else END),
    )
    graph.add_edge("extract", "gate_evidence")
    graph.add_conditional_edges(
        "gate_evidence",
        lambda state: "write"
        if not state.get("last_issues")
        else ("refine" if state.get("iteration", 0) < state.get("max_iterations", 0) else END),
    )
    graph.add_edge("write", "audit")
    graph.add_conditional_edges(
        "audit",
        lambda state: "compose"
        if state.get("gates", {}).get("g2_passed")
        else (
            "normalize_citations"
            if state.get("g2_route") == "normalize"
            else ("refine" if state.get("iteration", 0) < state.get("max_iterations", 0) else END)
        ),
    )
    graph.add_edge("normalize_citations", "compose")
    graph.add_edge("compose", "qa")
    graph.add_conditional_edges(
        "qa",
        lambda state: (
            "outline"
            if state.get("qa_route") == "outline"
            else (
                "compose"
                if state.get("qa_route") == "compose"
                else ("write" if state.get("qa_route") == "write" else "refine")
            )
        )
        if state.get("last_issues") and state.get("iteration", 0) < state.get("max_iterations", 0)
        else END,
    )
    graph.add_edge("refine", "retrieve")
    return graph


def run_pipeline(
    config: AgentConfig,
    inputs: PipelineInputs,
    emit: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None,
) -> PipelineState:
    graph = build_pipeline(config, emit)
    app = graph.compile()
    return app.invoke(_init_state(inputs, config), config={"recursion_limit": 100})
