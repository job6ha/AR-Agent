from __future__ import annotations

from typing import List

from .schemas import PipelineInputs


def parse_prompt(prompt: str) -> PipelineInputs:
    default_outline = [
        "관련 최신 기술동향",
        "원자력 분야 시뮬레이션 인공지능 사례",
        "노심 및 열수력 해석 난제",
        "멀티 피직스 결합 난제",
        "AI 모델 결합 시 난제",
        "연구 방향 제시",
    ]
    if not prompt:
        return PipelineInputs(
            raw_prompt="",
            topic="원자력 다중물리해석을 위한 AI 기반 시뮬레이션 최신 기술 동향 보고서",
            outline=default_outline,
        )
    return PipelineInputs(
        raw_prompt=prompt,
        topic="AR 기술동향 보고서",
        outline=[],
    )


def prompt_intro() -> str:
    return "작성할 보고서 프롬프트를 입력하세요. (끝내려면 빈 줄 2번)"


def collect_prompt_from_stdin() -> str:
    import sys

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print(prompt_intro())
    lines: List[str] = []
    empty_count = 0
    while True:
        line = input()
        if line.strip() == "":
            empty_count += 1
            if empty_count >= 2:
                break
            continue
        empty_count = 0
        lines.append(line)
    return "\n".join(lines).strip()
