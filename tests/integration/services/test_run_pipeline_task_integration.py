import asyncio
import os

from backend.domain.run_record import RunRecord
from backend.services.run_pipeline import run_pipeline_task


def test_run_pipeline_task_creates_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MOCK_MODE", "true")
    record = RunRecord(run_id="run1", prompt="test prompt")
    asyncio.run(run_pipeline_task(record))
    assert record.status.startswith("completed")
    assert record.artifacts_dir is not None
    report_path = os.path.join(record.artifacts_dir, "report.md")
    trace_path = os.path.join(record.artifacts_dir, "trace.md")
    assert os.path.exists(report_path)
    assert os.path.exists(trace_path)
