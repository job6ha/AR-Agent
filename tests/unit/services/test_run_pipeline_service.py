import json

from backend.services.run_pipeline import format_sse, format_timeline


def test_format_sse():
    payload = {"type": "status", "message": "ok"}
    text = format_sse(payload)
    assert text.startswith("data: ")
    assert json.dumps(payload, ensure_ascii=False) in text


def test_format_timeline():
    events = [
        {"type": "status", "agent": "planner", "message": "started", "ts": "t1", "payload": {"summary": "s1"}},
        {"type": "log", "agent": "system", "message": "skip", "ts": "t2", "payload": {}},
    ]
    output = format_timeline(events)
    assert "planner" in output
    assert "started" in output
