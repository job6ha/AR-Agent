import asyncio

from backend.services.run_service import RunManager, RunService, RunNotFound
from backend.domain.run_record import RunRecord


def test_run_manager_create_get_list():
    manager = RunManager()

    async def _run():
        record = await manager.create_run("prompt")
        fetched = await manager.get_run(record.run_id)
        runs = await manager.list_runs()
        return record, fetched, runs

    record, fetched, runs = asyncio.run(_run())
    assert record.run_id == fetched.run_id
    assert record in runs


def test_run_manager_get_missing():
    manager = RunManager()

    async def _run():
        try:
            await manager.get_run("missing")
        except RunNotFound:
            return True
        return False

    assert asyncio.run(_run()) is True


def test_run_service_start_run(monkeypatch):
    service = RunService()

    async def fake_task(_record):
        return None

    async def _run():
        monkeypatch.setattr("backend.services.run_service.run_pipeline_task", fake_task)
        monkeypatch.setattr("asyncio.create_task", lambda _coro: None)
        record = await service.start_run("prompt")
        return record

    record = asyncio.run(_run())
    assert isinstance(record, RunRecord)


def test_run_record_defaults():
    record = RunRecord(run_id="id1", prompt="prompt")
    assert record.status == "queued"
    assert record.errors == []


def test_run_service_stream_events():
    service = RunService()

    async def _run():
        record = await service._manager.create_run("prompt")
        record.events.append({"type": "status", "message": "m1"})
        record.events.append({"type": "done", "message": "done"})
        record.queue.put_nowait({"type": "done"})
        stream = await service.stream_events(record.run_id)
        events = []
        async for event in stream:
            events.append(event)
        return events

    events = asyncio.run(_run())
    assert any("m1" in event for event in events)


def test_run_service_get_report_path(tmp_path):
    service = RunService()

    async def _run():
        record = await service._manager.create_run("prompt")
        record.artifacts_dir = str(tmp_path)
        report_path = tmp_path / "report.md"
        report_path.write_text("report", encoding="utf-8")
        path = await service.get_report_path(record.run_id)
        return path

    path = asyncio.run(_run())
    assert path.endswith("report.md")


def test_run_service_get_report_path_not_ready():
    service = RunService()

    async def _run():
        record = await service._manager.create_run("prompt")
        try:
            await service.get_report_path(record.run_id)
        except Exception as exc:
            return str(exc)
        return ""

    message = asyncio.run(_run())
    assert "Artifacts not ready" in message


def test_run_service_get_report_path_missing(tmp_path):
    service = RunService()

    async def _run():
        record = await service._manager.create_run("prompt")
        record.artifacts_dir = str(tmp_path)
        try:
            await service.get_report_path(record.run_id)
        except Exception as exc:
            return str(exc)
        return ""

    message = asyncio.run(_run())
    assert "Report not found" in message
