from backend.domain.kaeri_ar_agent.prompts import load_prompts


def test_load_prompts_valid(tmp_path):
    data = "planner: |\n  hello\nwriter: |\n  world\n"
    path = tmp_path / "prompts.yaml"
    path.write_text(data, encoding="utf-8")
    prompts = load_prompts(str(path))
    assert prompts["planner"] == "hello"
    assert prompts["writer"] == "world"


def test_load_prompts_missing(tmp_path):
    prompts = load_prompts(str(tmp_path / "missing.yaml"))
    assert prompts == {}


def test_load_prompts_invalid(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    prompts = load_prompts(str(path))
    assert prompts == {}
