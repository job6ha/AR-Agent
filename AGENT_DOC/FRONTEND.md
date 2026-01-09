# FRONTEND.md (유연한 프론트엔드 구조 가이드: SvelteKit 라우팅 기반)

## 1. 목적

이 문서는 프론트엔드 코드가 다음을 만족하도록 **최소한의 구조 규칙**만 정의합니다.

* 에이전트가 새 파일을 **일관된 위치**에 생성/수정할 수 있다.
* UI/상태관리/스타일링 등 세부 구현은 **자유롭게 선택**할 수 있다.
* 페이지 파일에 모든 로직이 몰리거나, 컴포넌트가 여기저기 흩어지는 현상을 줄인다.

이 문서는 “정답 아키텍처”를 강제하지 않습니다. **파일 배치 기준과 경계(역할)** 만 제공합니다.

---

## 2. 전체 디렉터리 구조(권장)

```text
src/
  routes/                      # 라우팅(페이지). URL 구조와 1:1로 대응
  lib/
    features/                  # 기능(도메인) 단위 모듈: 기본 작업 위치(권장)
    shared/                    # 범용 재사용 자산(컴포넌트/유틸/API 헬퍼)
    app/                       # 앱 전역 설정/상수/세션 연결(작게 유지)
  styles/                      # 전역 스타일(선택)
```

### 새 코드는 어디에 두나? (에이전트 기준)

* 새 페이지(화면/URL): `src/routes/...`
* 기능 단위 코드(예: users, auth, reports): `src/lib/features/<기능명>/...`
* 여러 기능에서 공용으로 쓰는 것: `src/lib/shared/...`
* 전역 설정/상수: `src/lib/app/...`

---

## 3. 최소 원칙(강제 최소화)

### 3.1 “기능 우선(features-first)” 배치

페이지에 붙는 실질 코드는 가능하면 `src/lib/features/<기능명>/` 아래로 모읍니다.

* 예: 사용자 관리 기능이면 `features/users/` 아래에 컴포넌트/데이터 로직이 모이게 합니다.
* 이유: 에이전트와 사람이 “이 기능 관련 코드는 어디 있지?”를 즉시 찾을 수 있습니다.

### 3.2 routes는 비교적 얇게 유지(권장)

`src/routes`는 화면(페이지) 구성과 연결(조립) 위주로 두고,
복잡한 로직은 `features`로 내려가는 것을 우선 고려합니다.

단, 작은 페이지는 `+page.svelte` 안에서 간단히 끝내도 괜찮습니다(유연성 유지).

### 3.3 shared는 “진짜 공용”만

처음부터 shared로 올리지 말고, **일단 feature 내부에 두고** 재사용이 명확해지면 shared로 승격합니다.

### 3.4 의존성 방향(소프트 규칙)

기본적으로 아래 방향을 선호합니다.

```text
routes → features → shared
```

* `shared`는 `features`에 의존하지 않는 것을 권장합니다.
* `features`는 `routes`를 import하지 않는 것을 권장합니다.
* `routes`는 최상위이므로 필요한 모듈을 import할 수 있습니다.

※ 강제 “금지”는 아니지만, 이 방향을 따르면 구조가 무너지기 어렵습니다.

---

## 4. Feature 모듈 템플릿(유연형)

각 기능 폴더는 필요에 따라 아래 요소 중 일부만 사용합니다.
**모든 파일을 반드시 만들 필요는 없습니다.**

```text
src/lib/features/<feature>/
  components/                  # 기능 전용 UI 컴포넌트
  api.ts                       # 이 기능의 API 호출(선택)
  stores.ts                    # 이 기능 전용 상태(store) (선택)
  types.ts                     # 이 기능 타입/인터페이스(선택)
  services.ts                  # 여러 동작을 조합하는 유스케이스(선택)
  utils.ts                     # 기능 전용 유틸(선택)
  index.ts                     # 외부로 노출할 export 모음(선택)
```

### 운영 가이드(유연)

* 기능이 작으면 `components/` + `api.ts` 정도로 시작해도 충분합니다.
* 코드가 커지면 그때 `stores.ts`, `services.ts` 등을 추가합니다.

---

## 5. Shared 모듈 템플릿(유연형)

```text
src/lib/shared/
  components/                  # 범용 UI(버튼/모달/입력 등)
  api/                         # fetch 래퍼/에러 표준화 등 공통 API 헬퍼
  stores/                      # 전역 상태(테마/세션 등) — 최소화 권장
  utils/                       # 공용 유틸(포맷, 날짜 등)
  types/                       # 공용 타입
```

**원칙**: shared 코드는 가급적 “가벼운 의존성”을 유지합니다.

---

## 6. 라우팅(라우팅 기반 = SvelteKit 기본 방식) 가이드

SvelteKit에서는 `src/routes` 아래 파일 구조가 URL을 결정합니다.

* `src/routes/users/+page.svelte` → `/users`
* `src/routes/+layout.svelte` → 전역 레이아웃

### 최소 기대치(유연)

* `+page.svelte`: 페이지 UI (가능하면 조립 위주)
* `+page.ts`: 데이터 로딩이 필요할 때만 사용(선택)
* `+layout.svelte / +layout.ts`: 공통 레이아웃/공통 로딩(선택)

작은 프로젝트면 `+page.svelte` 안에서 간단히 데이터 호출해도 됩니다.
기능이 커지면 `features/<feature>/api.ts`로 내려 정리합니다.

---

## 7. 상태 관리(Store) 가이드(비강제)

특정 라이브러리/패턴을 강제하지 않습니다. 다만 “범위”만 권장합니다.

권장 우선순위:

1. 컴포넌트 로컬 상태(기본)
2. 기능 전용 store: `features/<feature>/stores.ts` (여러 컴포넌트가 공유할 때)
3. 전역 store: `shared/stores/` (정말 전역일 때만: 테마/세션 등)

에이전트는 전역 store를 쉽게 만들지 말고, 필요가 명확할 때만 도입합니다.

---

## 8. API 호출/에러 처리(가벼운 표준화)

프로젝트가 커질수록 API 호출이 흩어지기 쉬우므로, 아래 중 하나를 선택합니다.

### 옵션 A(권장): 공통 fetch 래퍼

* `src/lib/shared/api/http.ts`에 fetch 래퍼를 둔다(공통 헤더/에러 처리 등)
* 기능별 호출은 `features/<feature>/api.ts`가 담당한다

### 옵션 B: 기능별로만 관리

* 작은 프로젝트면 `features/<feature>/api.ts` 안에서 바로 fetch를 사용해도 된다
* 중복이 쌓이면 옵션 A로 승격한다

에이전트 기본 동작은:

* 엔드포인트가 몇 개 이상 생기면 옵션 A로 정리하는 것을 우선 고려합니다.

---

## 9. 네이밍 규칙(느슨하게)

* 기능 폴더: 소문자 (`users`, `auth`, `reports`)
* 컴포넌트: PascalCase (`UserTable.svelte`)
* 관례 파일명: `api.ts`, `stores.ts`, `types.ts`를 우선 사용

완벽한 네이밍보다 **일관성**을 우선합니다.

---

## 10. 에이전트 작업 지침(가장 중요)

새 기능을 개발할 때 에이전트는 아래 순서를 따릅니다.

1. 기능 소유 폴더를 결정한다 (`lib/features/<feature>/`)
2. UI는 `features/<feature>/components/`에 생성한다
3. 데이터 접근은 `features/<feature>/api.ts`에 둔다(필요 시)
4. `routes`는 가능한 한 “조립/연결” 중심으로 유지한다
5. 공용화가 명확해지면 shared로 옮긴다(처음부터 shared로 올리지 않음)

---

## 11. 예시(참고): Users 목록 페이지 추가

```text
src/
  routes/
    users/
      +page.svelte

  lib/
    features/
      users/
        components/
          UsersList.svelte
        api.ts
        types.ts
```

* `+page.svelte`는 `<UsersList />`를 렌더링하고, 필요하면 props만 전달
* `UsersList.svelte`는 `users/api.ts`를 호출하거나, 페이지에서 받아온 데이터를 표시
* 나중에 여러 화면에서 사용자 데이터가 필요해지면 `stores.ts`/`services.ts`를 추가

---

## 12. 이 문서가 일부러 강제하지 않는 것

유연성을 위해 다음은 강제하지 않습니다.

* 스타일링 방식(Tailwind/CSS/SCSS 등)
* 테스트 프레임워크 및 파일 배치
* 특정 상태관리 라이브러리
* 컴포넌트 아키텍처 정답(Atomic Design 등)

팀이 선호를 확정하면 “프로젝트 관례” 섹션을 아래에 덧붙이는 방식으로 확장합니다.
