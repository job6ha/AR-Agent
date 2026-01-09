from backend.domain.kaeri_ar_agent import AgentConfig, run_pipeline
from backend.domain.kaeri_ar_agent.prompting import collect_prompt_from_stdin, parse_prompt


def main():
    prompt = collect_prompt_from_stdin()
    inputs = parse_prompt(prompt)
    config = AgentConfig.from_env()
    state = run_pipeline(config, inputs)
    if state.get("errors"):
        print("Pipeline completed with issues:")
        for issue in state["errors"]:
            print(f"- {issue}")
    else:
        print(state.get("composed_text", "No output generated."))


if __name__ == "__main__":
    main()
