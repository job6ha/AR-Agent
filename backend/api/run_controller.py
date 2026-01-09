from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from backend.schemas.run import RunRequest, RunResponse, RunStatusResponse
from backend.services.run_service import (
    ArtifactsNotReady,
    ReportNotFound,
    RunNotFound,
    RunService,
)

router = APIRouter()
service = RunService()


@router.post("/api/run", response_model=RunResponse)
async def start_run(payload: RunRequest) -> RunResponse:
    record = await service.start_run(payload.prompt)
    return RunResponse(run_id=record.run_id)


@router.get("/api/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str) -> RunStatusResponse:
    try:
        record = await service.get_run(run_id)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(
        run_id=record.run_id,
        status=record.status,
        started_at=record.started_at,
        finished_at=record.finished_at,
        errors=record.errors,
        output_markdown=record.output_markdown,
    )


@router.get("/api/events/{run_id}")
async def stream_events(run_id: str) -> StreamingResponse:
    try:
        stream = await service.stream_events(run_id)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/api/artifacts/{run_id}/report.md")
async def download_report(run_id: str) -> FileResponse:
    try:
        path = await service.get_report_path(run_id)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")
    except ArtifactsNotReady:
        raise HTTPException(status_code=404, detail="Artifacts not ready")
    except ReportNotFound:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="text/markdown", filename="report.md")
