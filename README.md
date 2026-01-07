AR Report Agent
=====================

개요
----
- AR 기술동향 보고서를 “증거 기반 문서 조립” 방식으로 생성하는 에이전트 파이프라인.
- 증거 수집→검증→작성→감사까지 연계된 서비스 구조(FastAPI 백엔드, Svelte 프론트엔드).
- 실시간 에이전트 로그/LLM 스트리밍 및 실행 결과(report/trace/log) 저장 지원.

핵심 아이디어
------------
- Evidence-first: 근거(abstract/metadata) 기반으로만 문장 생성.
- 품질 게이트: G1(출처 무결성), G1b(증거 유효성), G2(인용 감사).
- 재시도 루프: 실패 시 쿼리 리파인 후 재수집.
- RAG(임베딩): arXiv abstract/metadata를 임베딩해 의미 기반 랭킹.

구성도
------
```text
User Prompt
   │
Outliner → Planner → Retriever(RAG) → G1 → Extractor → G1b → Writer → Auditor(G2) → Composer → QA
   │                                      └─ Refiner(쿼리 재작성) ──────────────────────────────┘
   └─ Logs/Streams → UI / runs/{run_id}/{report.md, trace.md, run.log}
```

폴더 구조
---------
- `backend/core/kaeri_ar_agent/agents/`: outliner/planner/retriever/extractor/writer/auditor/composer/qa/refiner
- `backend/core/kaeri_ar_agent/`: config, schemas, gates, pipeline, prompts
- `backend/main.py`: FastAPI 서버
- `backend/cli.py`: 로컬 CLI 실행
- `backend/prompts.yaml`: 에이전트 시스템 프롬프트
- `frontend/`: Svelte UI
- `reference/`: 참고 문서

빠른 시작
---------
1) 의존성 설치
```bash
uv sync
```

2) 환경변수 설정
```bash
cp .env.example .env
```

3) CLI 실행
```bash
python backend/cli.py
```

백엔드 실행
----------
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

프론트엔드 실행
--------------
```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`로 접속 후 프롬프트를 입력하면 파이프라인이 실행된다.
실행 중에는 에이전트 단계별 로그가 SSE로 스트리밍된다.
API 주소를 바꾸려면 `frontend/.env.example` 참고.

API 요약
--------
- `POST /api/run` : `{ "prompt": "..." }`로 실행 시작
- `GET /api/events/{run_id}` : SSE 로그 스트림
- `GET /api/runs/{run_id}` : 상태/에러/마크다운 결과 조회
- `GET /api/artifacts/{run_id}/report.md` : 결과 다운로드
- `GET /api/artifacts/{run_id}/trace.md` : 중간 과정 타임라인

설정
----
- `.env.example` 참고:
  - OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_EMBEDDING_MODEL`
  - 에이전트별 모델: `OUTLINER_MODEL`, `PLANNER_MODEL`, `RETRIEVER_MODEL`, `EXTRACTOR_MODEL`, `WRITER_MODEL`, `COMPOSER_MODEL`, `AUDITOR_MODEL`, `QA_MODEL`
  - Retrieval: `ARXIV_BASE_URL`, `REQUEST_TIMEOUT_S`, `REQUEST_RETRY_COUNT`, `REQUEST_RETRY_BACKOFF_S`
  - Limits: `MAX_SOURCES`, `MAX_EVIDENCE_PER_CHAPTER`, `MAX_QUERIES_PER_CHAPTER`, `MAX_QUERY_LENGTH`, `MAX_CONCURRENCY`
  - Gates: `G2_MODE` (`hard`/`soft`)
  - Prompts: `PROMPTS_PATH`

Docker 실행
-----------
1) 환경 변수 준비
```bash
cp .env.example .env
```

2) 전체 실행
```bash
make up
```

3) 종료
```bash
make down
```

포트
----
- API: `http://localhost:8000`
- UI: `http://localhost:5173`

산출물
------
- `runs/{run_id}/report.md`: 최종 보고서
- `runs/{run_id}/trace.md`: 에이전트 타임라인
- `runs/{run_id}/run.log`: 상세 JSONL 로그

코어 파이프라인
--------------
- `run_pipeline()`가 LangGraph 워크플로우를 실행.
- G1: DOI/URL 보유 + 1차 출처 포함 여부 확인.
- G1b: 챕터별 evidence 존재 여부 확인.
- G2: 인용 매핑 감사(soft 모드 시 경고로 기록).

입력 프롬프트 예시
------------------
```text
원자력 다중물리해석을 위한 AI 기반 시뮬레이션 최신 기술 동향 보고서 작성.
포맷: 연구원 제출용, 한글 서술형, 존칭 금지, 전문 문체.
구성: 초록/요약문/목차/제1장~제5장/참고문헌.
주제:
- 관련 최신 기술동향 (DeepMind 등 빅테크 연구결과, Genesis 프로젝트 언급)
- 원자력 분야 시뮬레이션 인공지능 사례
- 노심/열수력 해석의 어려움
- 멀티 피직스 결합의 어려움
- AI 모델 결합 시 난제
- 연구 방향 제시
제약:
- 근거 없는 수치/기관/프로젝트명 금지
- 본문 인용은 SourceRecord 기반으로만 생성
```

다음 단계
---------
- 벡터 DB 연동 및 사내 코퍼스 통합
- DOCX 템플릿 조립/다운로드
- 출처 유효성 자동 검증(doi/url resolve)
