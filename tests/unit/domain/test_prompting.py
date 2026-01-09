import io
import sys

from backend.domain.kaeri_ar_agent.prompting import (
    collect_prompt_from_stdin,
    parse_prompt,
    prompt_intro,
)


def test_parse_prompt_empty():
    inputs = parse_prompt("")
    assert inputs.topic
    assert inputs.outline


def test_parse_prompt_non_empty():
    inputs = parse_prompt("test prompt")
    assert inputs.raw_prompt == "test prompt"
    assert inputs.outline == []


def test_prompt_intro_text():
    assert "프롬프트" in prompt_intro()


def test_collect_prompt_from_stdin_non_tty(monkeypatch):
    data = io.StringIO("line1\nline2\n")
    monkeypatch.setattr(sys, "stdin", data)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    prompt = collect_prompt_from_stdin()
    assert prompt == "line1\nline2"


def test_collect_prompt_from_stdin_tty(monkeypatch):
    inputs = iter(["first line", "", "second line", "", ""])
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda: next(inputs))
    prompt = collect_prompt_from_stdin()
    assert prompt == "first line\nsecond line"
