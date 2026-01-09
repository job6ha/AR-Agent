from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, AsyncGenerator, Dict, List

from backend.domain.run_record import RunRecord
from backend.services.run_pipeline import format_sse, run_pipeline_task


class RunNotFound(Exception):
    pass


class ArtifactsNotReady(Exception):
    pass


class ReportNotFound(Exception):
    pass


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
            raise RunNotFound(f"Run {run_id} not found")
        return record

    async def list_runs(self) -> List[RunRecord]:
        async with self._lock:
            return list(self._runs.values())


class RunService:
    def __init__(self) -> None:
        self._manager = RunManager()

    async def start_run(self, prompt: str) -> RunRecord:
        record = await self._manager.create_run(prompt)
        asyncio.create_task(run_pipeline_task(record))
        return record

    async def get_run(self, run_id: str) -> RunRecord:
        return await self._manager.get_run(run_id)

    async def list_runs(self) -> List[RunRecord]:
        return await self._manager.list_runs()

    async def stream_events(self, run_id: str) -> AsyncGenerator[str, None]:
        record = await self._manager.get_run(run_id)

        async def event_stream() -> AsyncGenerator[str, None]:
            for event in record.events:
                yield format_sse(event)
            while True:
                event = await record.queue.get()
                yield format_sse(event)
                if event.get("type") == "done":
                    break

        return event_stream()

    async def get_report_path(self, run_id: str) -> str:
        record = await self._manager.get_run(run_id)
        if not record.artifacts_dir:
            raise ArtifactsNotReady("Artifacts not ready")
        path = os.path.join(record.artifacts_dir, "report.md")
        if not os.path.exists(path):
            raise ReportNotFound("Report not found")
        return path
