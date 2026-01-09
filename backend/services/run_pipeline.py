from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.domain.run_record import RunRecord
from backend.domain.kaeri_ar_agent import AgentConfig, run_pipeline
from backend.domain.kaeri_ar_agent.prompting import parse_prompt


def format_sse(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n"


def format_timeline(events: List[Dict[str, Any]]) -> str:
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


async def run_pipeline_task(record: RunRecord) -> None:
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
        unused_sources = [
            source
            for source in sources
            if (source.canonical_source_id or source.source_id) not in cited_ids
        ]
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
                source_id = source.canonical_source_id or source.source_id
                title = source.title or source_id
                link = source.url or source.doi or ""
                if link:
                    markdown += f"- {title} ({source_id}) - {link}\n"
                else:
                    markdown += f"- {title} ({source_id})\n"
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
            handle.write(format_timeline(record.events))
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
