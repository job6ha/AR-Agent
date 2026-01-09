# TESTING.md (Backend: pytest + coverage, 유연형 가이드)

## 0. 핵심 규칙 요약 (에이전트 우선)
1) 새 기능/수정에는 반드시 테스트를 추가한다. (MUST)  
2) “있는 함수는 전부 테스트한다”를 기본 원칙으로 한다. (MUST)  
3) 테스트 케이스는 엣지케이스 중심으로 작성하되, 정상 동작 확인 케이스도 포함한다. (MUST)  
4) Domain(Core)은 순수 단위테스트 중심, Service는 유스케이스 단위, API는 계약/통합 테스트로 구성한다. (SHOULD)  
5) 외부 의존(DB/외부 API)은 기본적으로 mocking 또는 테스트 더블로 격리한다. (SHOULD)  
6) 커버리지는 항상 측정하고, CI에서 리포트를 생성한다. (MUST)  
7) flaky 테스트(불안정)는 금지하며, 시간/랜덤/네트워크 의존을 제거한다. (MUST)  
8) 테스트는 독립적이어야 하며, 실행 순서에 의존하지 않는다. (MUST)  
9) 실패 시 원인이 즉시 드러나도록 assert를 명확히 쓴다. (MUST)  
10) 테스트가 어렵다면 코드 구조(의존성/순수성)를 개선하는 것이 우선이다. (SHOULD)

---

## 1. 목표
- 백엔드 코드의 기능을 자동화된 테스트로 검증한다.
- 엣지케이스 중심으로 결함을 조기에 탐지한다.
- 커버리지 리포트를 표준화하여 품질을 가시화한다.
- 에이전트가 테스트 파일 위치/형식을 일관되게 생성할 수 있도록 기준을 제공한다.

---

## 2. 테스트 범위(기본 원칙)
### 2.1 “함수는 전부 테스트한다”
- `app/` 하위의 “의미 있는 함수/메서드”는 모두 테스트 대상이다.
- 단순한 getter/setter 수준이거나, 외부 라이브러리 thin wrapper만 있는 경우는 예외가 될 수 있으나,
  기본은 **전부 테스트**로 간주한다.

### 2.2 케이스 설계 원칙
테스트 케이스는 다음을 균형 있게 포함한다.

1) **엣지케이스(우선)**  
   - 빈 값/None/누락 필드  
   - 타입이 다름(문자열 대신 숫자 등)  
   - 경계값(min/max, 길이 0/1/최대, 범위 밖)  
   - 특수문자/유니코드/공백/개행  
   - 중복/정렬/순서 무관 요구사항  
   - 시간/타임존 경계(해당 시)  
   - 예외가 발생해야 하는 입력

2) **타당한 정상 케이스(기본 기능 확인)**  
   - “사용자가 실제로 넣을 법한” 대표 입력  
   - 정상 출력/부수효과(저장/조회/상태 변화) 확인

---

## 3. 테스트 레이어 전략(권장)
본 프로젝트는 백엔드를 다음 레벨로 테스트한다(세부는 유연).

### 3.1 Domain(Core) 단위 테스트 (unit)
- 대상: `app/domain/**`
- 특징: 외부 의존 없이 순수 함수/규칙을 빠르게 검증
- 목적: 엣지케이스와 규칙 위반을 촘촘히 검증

### 3.2 Service 유스케이스 테스트 (unit-ish / component)
- 대상: `app/services/**`
- 특징: repository/integration을 mocking하여 유스케이스 흐름 검증
- 목적: 조합 로직, 트랜잭션 경계, 예외 흐름 검증

### 3.3 API 계약/통합 테스트 (integration)
- 대상: `app/api/**`
- 특징: 테스트 클라이언트로 엔드포인트 호출
- 목적: request/response 스키마, status code, 에러 포맷, 인증/인가 연결 검증
- 외부 의존(DB 등)은 “테스트 전용 환경” 또는 “mock” 중 프로젝트 상황에 맞춰 선택

---

## 4. 디렉터리/네이밍 규칙
### 4.1 기본 구조
```text
tests/
  unit/
    domain/
    services/
  integration/
    api/
  fixtures/
    data/               # 정적 샘플 데이터(JSON 등, 선택)
  conftest.py
````

### 4.2 파일 네이밍

* 테스트 파일: `test_<module>.py`
* 테스트 함수: `test_<behavior>_<condition>()`
* 클래스 기반도 가능하나 pytest에서는 함수 기반을 기본으로 한다.

---

## 5. pytest 실행 표준(커맨드)

### 5.1 권장 의존성

* pytest
* pytest-cov
* (선택) pytest-mock
* (선택) hypothesis (프로퍼티 기반 테스트가 필요할 때)

### 5.2 로컬 실행(예시)

```bash
pytest
pytest -q
pytest -q -k "keyword"
```

### 5.3 커버리지 측정(권장)

```bash
pytest --cov=app --cov-report=term-missing
pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing
```

* `term-missing`: 어떤 라인이 빠졌는지 터미널에서 바로 확인
* `html`: `htmlcov/` 생성(사람이 보기 좋음)
* `xml`: CI/배지/품질도구 연동에 유리

### 5.4 커버리지 게이트(권장)

```bash
pytest --cov=app --cov-fail-under=85 --cov-report=term-missing
```

* 초기에는 70~85 정도로 시작하고, 코드 안정화에 따라 상향 권장
* “함수 전부 테스트” 원칙이라면 장기적으로 90+가 목표가 될 수 있음

---

## 6. 커버리지 설정 파일(권장)

프로젝트 루트에 `.coveragerc`를 두는 것을 권장한다.

```ini
[run]
branch = True
source = app
omit =
  */__init__.py
  */migrations/*
  */alembic/*
  */tests/*
  */venv/*
  */.venv/*

[report]
show_missing = True
skip_covered = False
precision = 1
exclude_lines =
  pragma: no cover
  if __name__ == .__main__.:
  raise NotImplementedError
  @abstractmethod
```

* `branch=True`: 분기 커버리지(조건문)까지 확인
* `omit`: 테스트/마이그레이션 등 제외

---

## 7. pytest 설정 파일(권장)

프로젝트 루트에 `pytest.ini` 또는 `pyproject.toml`로 설정을 고정한다.

예: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts =
  -ra
  --strict-markers
  --disable-warnings
markers =
  unit: unit tests
  integration: integration tests
```

---

## 8. Fixtures 전략 (pytest 방식)

### 8.1 기본 원칙

* fixture는 “공유 설정/공유 데이터”에만 사용한다.
* 과도한 fixture 체인은 가독성을 떨어뜨리므로 최소화한다.

### 8.2 권장 fixture 범위

* 공통 샘플 데이터(정상/엣지) 생성기
* mock repository / mock integration client
* (API 통합) 테스트 클라이언트 생성

---

## 9. Mocking / 외부 의존 격리 원칙

### 9.1 기본 원칙

* 네트워크 호출은 금지(테스트 불안정/느림).
* 시간/랜덤 의존은 고정한다(주입 가능하게 만들거나 monkeypatch).

### 9.2 어디를 mock하나?

* `services` 테스트: repository/integration을 mock으로 대체
* `api` 통합 테스트: 인증/외부 연동은 상황에 따라 mock 또는 테스트 더블 사용

---

## 10. 엣지케이스 체크리스트(에이전트용)

다음 항목을 우선 고려해 케이스를 작성한다.

* None / 빈 문자열 / 빈 리스트 / 빈 dict
* 누락 필드 / 추가 필드
* 잘못된 타입(문자열↔숫자 등)
* 길이 경계(0, 1, max-1, max, max+1)
* 범위 경계(min-1, min, max, max+1)
* 중복 입력, 순서 무관 요구사항
* 특수문자/유니코드/공백/개행
* 예외가 발생해야 하는 입력(정책 위반)
* 큰 입력(성능이슈 가능 범위 내)
* 동시성/재시도 로직이 있다면 재현 가능한 최소 케이스

---

## 11. 테스트 작성 템플릿(권장 패턴)

### 11.1 Arrange-Act-Assert(AAA)

* Arrange: 입력/fixture 구성
* Act: 함수 호출
* Assert: 결과/예외/부수효과 검증

### 11.2 예외 테스트는 명확히

* 어떤 예외 타입인지
* 메시지/에러코드가 있다면 그것도 검증

---

## 12. CI에서 리포트 생성(권장)

CI에서는 아래를 기본으로 한다.

* `pytest --cov=app --cov-report=xml --cov-report=term-missing --cov-fail-under=<threshold>`
* 빌드 아티팩트로 `coverage.xml` 또는 `htmlcov/` 업로드(가능 시)

---

## 13. 에이전트 작업 지침(구현 시)

새 코드 추가/수정 시 에이전트는 반드시:

1. 해당 모듈의 테스트 파일을 찾거나 생성한다.
2. 새로 생긴 함수/분기/예외 흐름을 테스트로 추가한다.
3. 엣지케이스 + 정상 케이스를 최소 1개 이상 포함한다.
4. 커버리지 리포트에서 누락 라인을 확인하고 보완한다.

```

---

원하시면, 위 `TESTING.md`와 함께 레포에 바로 넣을 수 있는 **기본 파일 세트**도 만들어 드릴 수 있습니다.

- `pytest.ini`
- `.coveragerc`
- `tests/conftest.py`(기본 fixture 템플릿)
- `Makefile` 또는 `justfile`로 `make test`, `make cov` 같은 단축 명령
