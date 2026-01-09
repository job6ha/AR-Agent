AR Report Agent
=====================

개요
----
- AR 기술동향 보고서를 “증거 기반 문서 조립” 방식으로 생성하는 에이전트 파이프라인.
- 증거 수집→검증→작성→감사→QA까지 연계된 서비스 구조(FastAPI 백엔드, Svelte 프론트엔드).
- 실시간 에이전트 로그/LLM 스트리밍 및 실행 결과(report/trace/log) 저장 지원.

핵심 아이디어
------------
- Evidence-first: 근거(abstract/metadata) 기반으로만 문장 생성(원문 전문 사용 없음).
- 품질 게이트: G1(출처 무결성), G1a(멀티 소스 합의), Status(철회/정정), G1b(증거 유효성), G2(인용 감사), QA(문체/구성 점검).
- 재시도 루프: 실패 원인에 따라 쿼리 리파인 또는 재작성.
- RAG(임베딩): arXiv abstract/metadata를 임베딩해 챕터별 의미 기반 랭킹.
- 인용 정규화: S-ARXIV-* 포맷을 arXiv:*로 정리.
- 정본화(canonicalization): DOI 우선으로 SourceRecord를 정본 메타데이터로 승격, canonical_source_id 기반 인용 강제.

구성도
------
```text
User Prompt
   │
Outliner → Planner → Retriever(RAG) → G1 → Resolver → G1a(Consensus) → Status → Extractor → G1b → Writer → Auditor(G2) → Composer → QA
   │                               │                               │                └─ Normalize ──────────────────────┘
   │                               └─ Refiner(쿼리/해결 재작성) ─────┴────────────────────────────────────────────────────┘
   └─ Logs/Streams → UI / runs/{run_id}/{report.md, trace.md, run.log}
```

폴더 구조
---------
- `backend/domain/kaeri_ar_agent/agents/`: outliner/planner/retriever/resolver/status_checker/extractor/writer/auditor/composer/qa/refiner
- `backend/domain/kaeri_ar_agent/providers/`: crossref/openalex/semanticscholar/unpaywall 커넥터
- `backend/domain/kaeri_ar_agent/gates/`: g1, g1a(consensus), g2
- `backend/domain/kaeri_ar_agent/`: config, schemas, pipeline, prompts
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
  - `runs/{run_id}/trace.md`는 서버 파일로 저장되며 API는 제공하지 않는다.

설정
----
- `.env.example` 참고:
  - 사용 방법: `cp .env.example .env` 후 값 채우기 (프로덕션은 별도 비밀 관리 권장).
  - mock_mode 테스트: `MOCK_MODE=true`로 두면 외부 API/LLM 없이 샘플 데이터로 파이프라인 점검 가능.
  - OpenAI:
    - `OPENAI_API_KEY`: OpenAI API 키.
    - `OPENAI_MODEL`: 기본 LLM 모델명.
    - `OPENAI_TEMPERATURE`: 기본 샘플링 온도.
    - `OPENAI_EMBEDDING_MODEL`: 임베딩 모델명(RAG 랭킹용).
  - 에이전트별 모델:
    - `OUTLINER_MODEL`, `PLANNER_MODEL`, `RETRIEVER_MODEL`, `EXTRACTOR_MODEL`, `WRITER_MODEL`, `COMPOSER_MODEL`, `AUDITOR_MODEL`, `QA_MODEL`: 각 에이전트 전용 모델 오버라이드.
    - `*_TEMPERATURE`: 해당 에이전트 전용 온도 오버라이드.
  - Retrieval:
    - `ARXIV_BASE_URL`: arXiv API 엔드포인트.
    - `REQUEST_TIMEOUT_S`: 외부 요청 타임아웃(초).
    - `REQUEST_RETRY_COUNT`: 요청 재시도 횟수.
    - `REQUEST_RETRY_BACKOFF_S`: 재시도 간 백오프(초).
  - Providers:
    - `OPENALEX_MAILTO`: OpenAlex 요청 시 mailto 파라미터(권장).
    - `UNPAYWALL_EMAIL`: Unpaywall API 필수 이메일.
    - `SEMANTICSCHOLAR_API_KEY`: Semantic Scholar API 키(선택).
    - `PROVIDER_TIMEOUT_S`: provider 호출 타임아웃(초).
    - `MAX_PROVIDER_CONCURRENCY`: provider 동시 호출 제한.
  - Limits:
    - `MAX_SOURCES`: 전체 출처 상한.
    - `MAX_EVIDENCE_PER_CHAPTER`: 챕터별 evidence 상한.
    - `MAX_QUERIES_PER_CHAPTER`: 챕터별 검색 쿼리 상한.
    - `MAX_QUERY_LENGTH`: 쿼리 길이 제한.
    - `MAX_CONCURRENCY`: LLM/추출 동시 처리 제한.
    - `MAX_ITERATIONS`: refine 재시도 상한.
  - Gates:
    - `G2_MODE`: 인용 감사 게이트 모드(`hard`/`soft`).
    - `VERIFY_MODE`: 정본 검증/상태 체크 게이트 모드(`hard`/`soft`).
    - `MOCK_MODE`: 샘플 데이터로 동작(true/false).
  - Prompts:
    - `PROMPTS_PATH`: 시스템 프롬프트 YAML 경로.

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
- `runs/{run_id}/trace.md`: 에이전트 타임라인(LLM 스트림 포함)
- `runs/{run_id}/run.log`: 상세 JSONL 로그(실시간 append)

코어 파이프라인
--------------
- `run_pipeline()`가 LangGraph 워크플로우를 실행.
- Outliner: 프롬프트에서 주제/목차/범위/제외 범위를 생성.
- Planner: 챕터별 검색 쿼리 생성.
- Retriever: arXiv API 호출 후 임베딩 랭킹으로 출처 선택.
- G1: DOI/URL 보유 + 1차 출처 포함 여부 확인.
- Resolver: DOI 우선 정본화(canonicalization). DOI가 없으면 OpenAlex/S2 검색 후 Crossref로 확정.
- G1a(Consensus): Crossref + OpenAlex/S2 합의 점수로 통과/보류/반려 결정(점수/사유는 trace/run.log에 기록).
- Status: 철회/정정/EoC 상태 확인 후 정책 적용(retracted는 제외, correction/eoc는 경고).
- Extractor: abstract 요약으로 evidence 스니펫 생성(인용은 canonical_source_id 사용).
- G1b: 챕터별 evidence 존재 여부 확인.
- Writer: evidence 기반으로 본문 작성(인용은 `canonical_source_id`).
- G2: 인용 매핑 감사(soft 모드 시 경고 기록). 포맷 이슈는 인용 정규화 후 진행.
- Composer: 초록/키워드(LLM 사용 시) + 본문/방법론/참고문헌 조립(참고문헌은 canonical metadata 기반).
- QA: 문체/구성 점검 후 필요 시 outline/compose/write/refine로 되돌림.

참고문헌 정본화 규칙
-------------------
- canonical_source_id는 `doi:...` 우선, 없으면 `arxiv:...`로 설정.
- preprint-only는 참고문헌에 `[preprint]` 라벨로 표기.
- reference는 canonical metadata(title/authors/year/venue/doi/url) 기반으로 재조립.

검증 근거/감사 로그
-------------------
- `run.log`: provider 호출 결과, 합의 점수/사유, 상태 플래그를 JSONL로 누적.
- `trace.md`: 단계별 요약(Resolver 결과, G1a 점수, Status 플래그 포함).

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
- 캐싱/레이트리밋/서킷브레이커(429 폭주 방지)
- QA 룰에 “출처 상태/정본 인용” 점검 추가
