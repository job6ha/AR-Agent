from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

import sys

from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

from kaeri_ar_agent import AgentConfig, run_pipeline
from kaeri_ar_agent.prompting import parse_prompt


@dataclass
class RunRecord:
    run_id: str
    prompt: str
    status: str = "queued"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    output_markdown: Optional[str] = None
    artifacts_dir: Optional[str] = None
    log_path: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class RunManager:
    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()

    async def create_run(self, prompt: str) -> RunRecord:
        run_id = uuid.uuid4().hex
        record = RunRecord(run_id=run_id, prompt=prompt)
        async with self._lock:
            self._runs[run_id] = record
        return record

    async def get_run(self, run_id: str) -> RunRecord:
        async with self._lock:
            record = self._runs.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        return record

    async def list_runs(self) -> List[RunRecord]:
        async with self._lock:
            return list(self._runs.values())


load_dotenv()

app = FastAPI(title="KAERI AR Agent API")
manager = RunManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_sse(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _format_timeline(events: List[Dict[str, Any]]) -> str:
    lines = ["## 에이전트 타임라인"]
    for event in events:
        if event.get("type") != "status":
            continue
        agent = event.get("agent", "system")
        message = event.get("message", "")
        ts = event.get("ts", "")
        summary = ""
        payload = event.get("payload") or {}
        if isinstance(payload, dict):
            summary = payload.get("summary", "")
        lines.append(f"- [{ts}] {agent}: {message} {f'— {summary}' if summary else ''}")
        if payload:
            lines.append("```json")
            lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
            lines.append("```")
    return "\n".join(lines) + "\n"


async def _run_pipeline(record: RunRecord) -> None:
    record.status = "running"
    record.started_at = datetime.utcnow().isoformat()
    loop = asyncio.get_running_loop()
    artifacts_dir = os.path.join("runs", record.run_id)
    os.makedirs(artifacts_dir, exist_ok=True)
    record.artifacts_dir = artifacts_dir
    record.log_path = os.path.join(artifacts_dir, "run.log")

    def log_event(event: Dict[str, Any]) -> None:
        if not record.log_path:
            return
        with open(record.log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        print(json.dumps(event, ensure_ascii=False), flush=True)

    def emit(agent: str, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        event_type = "status"
        if payload and isinstance(payload, dict):
            payload_type = payload.get("type")
            if isinstance(payload_type, str) and payload_type.startswith("llm_stream"):
                event_type = payload_type
        event = {
            "type": event_type,
            "agent": agent,
            "message": message,
            "ts": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        record.events.append(event)
        log_event(event)
        loop.call_soon_threadsafe(record.queue.put_nowait, event)

    try:
        log_event(
            {
                "type": "run_started",
                "ts": record.started_at,
                "prompt": record.prompt,
            }
        )
        config = AgentConfig.from_env()
        inputs = parse_prompt(record.prompt)
        state = await asyncio.to_thread(run_pipeline, config, inputs, emit)
        record.errors = list(state.get("errors", []))
        warnings = list(state.get("warnings", []))
        output = state.get("composed_text") or ""
        sources = state.get("sources", [])
        drafts = state.get("drafts", [])
        cited_ids = {cid for draft in drafts for cid in draft.citation_source_ids}
        unused_sources = [source for source in sources if source.source_id not in cited_ids]
        markdown = "# Pipeline Output\n\n"
        if output:
            markdown += output + "\n\n"
        if warnings:
            markdown += "## Citation Warnings\n"
            for warning in warnings:
                markdown += f"- {warning}\n"
            markdown += "\n"
        if unused_sources:
            markdown += "## Retrieved But Unused Sources\n"
            for source in unused_sources:
                title = source.title or source.source_id
                link = source.url or source.doi or ""
                if link:
                    markdown += f"- {title} ({source.source_id}) - {link}\n"
                else:
                    markdown += f"- {title} ({source.source_id})\n"
            markdown += "\n"
        if record.errors:
            markdown += "## Issues\n"
            for issue in record.errors:
                markdown += f"- {issue}\n"
        record.output_markdown = markdown
        report_path = os.path.join(artifacts_dir, "report.md")
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        trace_path = os.path.join(artifacts_dir, "trace.md")
        with open(trace_path, "w", encoding="utf-8") as handle:
            handle.write(_format_timeline(record.events))
        record.status = "completed" if not record.errors else "completed_with_issues"
    except Exception as exc:
        record.status = "failed"
        record.errors.append(str(exc))
    finally:
        record.finished_at = datetime.utcnow().isoformat()
        done_event = {
            "type": "done",
            "status": record.status,
            "ts": datetime.utcnow().isoformat(),
        }
        record.events.append(done_event)
        log_event(
            {
                "type": "run_finished",
                "ts": record.finished_at,
                "status": record.status,
                "errors": record.errors,
                "artifacts_dir": record.artifacts_dir,
            }
        )
        await record.queue.put(done_event)


@app.post("/api/run")
async def start_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = payload.get("prompt", "")
    record = await manager.create_run(prompt)
    asyncio.create_task(_run_pipeline(record))
    return {"run_id": record.run_id}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    record = await manager.get_run(run_id)
    return {
        "run_id": record.run_id,
        "status": record.status,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "errors": record.errors,
        "output_markdown": record.output_markdown,
    }


@app.get("/api/events/{run_id}")
async def stream_events(run_id: str) -> StreamingResponse:
    record = await manager.get_run(run_id)

    async def event_stream() -> Any:
        for event in record.events:
            yield _format_sse(event)
        while True:
            event = await record.queue.get()
            yield _format_sse(event)
            if event.get("type") == "done":
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/artifacts/{run_id}/report.md")
async def download_report(run_id: str) -> FileResponse:
    record = await manager.get_run(run_id)
    if not record.artifacts_dir:
        raise HTTPException(status_code=404, detail="Artifacts not ready")
    path = os.path.join(record.artifacts_dir, "report.md")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="text/markdown", filename="report.md")
