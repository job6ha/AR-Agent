#!/bin/bash
# setup_env.sh - 작업 시작할 때마다 실행하세요! (source setup_env.sh)

# 프로젝트 루트 경로 자동 계산
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 1. uv 가상환경 활성화
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo "⚠️ 가상환경이 없습니다. 'bash install.sh'를 먼저 실행하세요."
    return
fi

# 2. 테스트에서 backend 모듈을 찾을 수 있도록 PYTHONPATH 설정
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# 3. 간단 테스트 헬퍼(선택)
ar_test() {
    uv run pytest -q "$@"
}

echo "✅ [AR-Agent] 환경 활성화 완료!"
