# Python 백엔드 레이어드 아키텍처 제안서 (Spring Boot 스타일 응용)

## 1. 목적과 배경

Python 백엔드 프로젝트에서 코드가 “어지러워지는” 주요 원인은 다음과 같습니다.

* HTTP 처리(라우팅/상태코드/인증 등)와 비즈니스 로직이 뒤섞임
* DB/외부 연동 코드가 여기저기 흩어져 변경 영향 범위가 커짐
* 테스트가 어려워지고, 결과적으로 기능 추가·수정이 느려짐

이에 따라, Spring Boot에서 흔히 사용하는 **레이어드 아키텍처**를 Python 백엔드에 적용하되, Python 생태계 관례에 맞게 조정한 구조를 제안합니다.

---

## 2. 제안 아키텍처 개요

### 2.1 핵심 레이어 정의

아래 레이어는 **책임 분리(Separation of Concerns)** 를 통해 유지보수성과 테스트 용이성을 확보합니다.

* **Schemas/DTO 레이어**: 요청/응답 데이터 구조 정의 및 검증
* **Controller(API) 레이어**: 엔드포인트(라우터) 모음, HTTP concern 처리
* **Service 레이어**: 유스케이스(업무 흐름) 오케스트레이션, 트랜잭션 경계
* **Domain(Core) 레이어**: 도메인 규칙과 순수 로직(가능한 한 외부 의존 최소화)
* (선택) **Repository 레이어**: DB 접근 캡슐화
* (선택) **Integration/Adapter 레이어**: 외부 API, 메시징, 파일스토리지 등 연동 캡슐화

---

## 3. 레이어별 책임과 규칙

## 3.1 Schemas / DTO

### 역할

* Request/Response 스키마 정의
* 입력 검증(validation) 및 직렬화/역직렬화
* API 계약(Contract)의 명시화

### 권장 사항 (Python 관례)

* FastAPI를 사용할 경우 `pydantic` 모델을 DTO로 활용하는 것이 일반적이며 실무적으로 효율적입니다.
* “전송만 하는 DTO”로 제한하면 검증 로직이 분산되어 오히려 복잡해질 수 있습니다.

### 금지/주의

* DB 세션, ORM 모델, 외부 SDK를 직접 참조하지 않도록 합니다.
* 비즈니스 규칙(도메인 정책)을 DTO에 넣지 않습니다.

---

## 3.2 Controller (API / Router)

### 역할

* 엔드포인트 정의(라우팅)
* HTTP 관련 처리: 상태코드, 헤더, 요청 파라미터 매핑
* 인증/인가 미들웨어 또는 dependency 연결
* Service 호출 및 응답 구성

### 설계 원칙

* Controller는 **얇게(thin)** 유지합니다.
* “HTTP → 서비스 호출 → 응답” 흐름으로 제한합니다.

### 금지/주의

* 도메인 로직을 controller에 구현하지 않습니다.
* DB/외부 API 호출을 controller에서 직접 수행하지 않습니다.

---

## 3.3 Service (Use Case / Application Service)

### 역할

* 유스케이스 단위의 오케스트레이션(업무 흐름 조합)
* 트랜잭션 경계 설정(필요 시)
* Repository/Integration을 호출해 side-effect를 통제
* 권한/정책 적용(프로젝트 성격에 따라 service에서 수행하는 것이 관리가 용이)

### 설계 원칙

* 서비스는 “업무 시나리오 단위”로 구성합니다.
* 도메인 로직은 domain(core)로 위임하고, service는 조합/흐름 제어에 집중합니다.

### 금지/주의

* service가 모든 로직을 빨아들이는 “거대 서비스”가 되지 않도록 유의합니다.
* 순수 계산/규칙은 domain으로 내립니다.

---

## 3.4 Domain / Core

### 역할

* 핵심 비즈니스 규칙과 도메인 정책(불변조건, 계산 규칙)
* 가능한 한 **순수 함수/순수 로직** 중심(입력 → 출력)
* 외부 의존성을 최소화하여 테스트 용이성 확보

### 설계 원칙

* domain은 “인프라(HTTP/DB/외부 API)”로부터 독립적이어야 합니다.
* 로직이 복잡해질수록 domain의 가치가 커집니다(테스트 비용 감소, 재사용성 증가).

### 금지/주의

* DB 세션/ORM, 외부 API SDK, 프레임워크 객체를 직접 참조하지 않습니다.
* 네트워크 호출, 파일 IO 같은 side-effect는 integration/service 계층으로 올립니다.

---

## 3.5 Repository (선택)

### 역할

* 데이터 영속성(DB) 접근을 캡슐화
* ORM/SQLAlchemy, Query 로직을 한 곳에 격리
* service는 repository 인터페이스만 사용하도록 유도

### 기대 효과

* DB 변경(ORM 교체, 스키마 변경)의 영향 범위를 repository로 제한
* 테스트 시 repository mocking이 쉬워짐

---

## 3.6 Integration / Adapter (선택)

### 역할

* 외부 API, 메시지큐, S3/파일스토리지, 사내 시스템 연동 등을 격리
* 외부 SDK 사용을 한곳으로 모아 변경에 강한 구조 확보

### 기대 효과

* 외부 연동 스펙 변경 시 service/domain을 덜 흔들고 대응 가능

---

## 4. 권장 디렉터리 구조 예시 (Python 백엔드)

아래 예시는 Spring 스타일을 유지하면서 Python 관례(특히 FastAPI)에 맞춘 형태입니다.

```text
app/
  api/                  # controller (router)
    v1/
      users.py
      health.py

  schemas/              # dto (request/response schemas)
    user.py
    common.py

  services/             # service (use cases)
    user_service.py
    auth_service.py

  domain/               # core (domain rules, pure logic)
    user.py             # domain entities/value objects (선택)
    policies.py         # business rules
    calculators.py      # pure functions

  repositories/         # repository (DB access)
    user_repo.py
    base.py

  integrations/         # external services (API clients, MQ, etc.)
    slack_client.py
    storage_client.py

  common/               # cross-cutting
    config.py
    exceptions.py
    logging.py
    utils.py

  main.py               # app entrypoint
```

---

## 5. 의존성 방향(Dependency Rule)

구조가 “어지러워지지” 않게 만드는 핵심 규칙은 **의존성 방향**입니다.

권장 의존성 흐름:

```text
Controller(API) → Service → (Repository / Integration) → Infrastructure
                     ↓
                  Domain(Core)
```

* Domain(Core)은 가능한 한 “위쪽 레이어”에 의존하지 않습니다.
* Controller는 Domain을 직접 호출하기보다 Service를 통해 호출하는 편이 일관성이 좋습니다(프로젝트 규모가 커질수록 유리).

---

## 6. 테스트 전략(권장)

* **Domain(Core)**: 단위 테스트 중심 (순수 로직이므로 빠르고 안정적)
* **Service**: 유스케이스 단위 테스트 (repository/integration mocking)
* **Controller(API)**: 계약 테스트 중심 (요청/응답 스키마 및 status code 확인)

이 구조는 테스트 피라미드를 자연스럽게 유도하여, 기능 추가 속도와 안정성을 동시에 높입니다.

---

## 7. 흔한 실패 패턴 및 예방책

### 7.1 과도한 추상화

* 엔드포인트 하나 구현하는데 클래스/파일이 과도하게 늘어나는 현상
* 예방: 작은 프로젝트에서는 레이어를 “필요할 때만” 도입하고, 얇은 래퍼만 만들지 않도록 합니다.

### 7.2 Service 비대화

* 모든 로직이 service로 모여 “거대 서비스”가 되는 현상
* 예방: 규칙/계산은 domain(core)로 내리고, service는 오케스트레이션에 집중합니다.

### 7.3 Core에 인프라 침투

* core/domain에 DB 세션, SDK 객체가 들어오는 현상
* 예방: repository/integration으로 side-effect를 격리하고 core는 순수화합니다.

---

## 8. 결론 및 적용 권고

제안 구조(dto/controller/service/core)는 Python 백엔드에서도 충분히 타당하며, 특히 다음 상황에서 강력히 권장됩니다.

* 팀 개발(유지보수자 다수), 기능 확장 가능성이 높음
* 비즈니스 규칙이 복잡하거나 점점 복잡해질 예정
* 테스트 및 품질 관리가 중요한 프로젝트

추가로, 실무 안정성을 높이기 위해 **Repository/Integration 레이어를 필요에 따라 추가**하는 것을 권장합니다.
