# Roadmap v1.11.0 ~ v2.0.0 -- Final Consensus

> **Status**: Approved
> **Date**: 2026-02-26
> **Participants**: Dev Architect, Product/UX Strategist, Technical Program Manager (mediator)
> **Base version**: v1.10.0 (utils.py, AST 검증, JSON sidecar, 스케줄 DRY, Slack 재시도, 테스트 프레임워크)

---

## Table of Contents

1. [쟁점 해결 결과](#쟁점-해결-결과)
2. [v1.11.0 -- Weekly Briefing & Foundation](#v1110----weekly-briefing--foundation)
3. [v1.12.0 -- Unified Notification System](#v1120----unified-notification-system)
4. [v2.0.0 -- Multi-Channel & Major Upgrade](#v200----multi-channel--major-upgrade)
5. [Timeline Summary](#timeline-summary)
6. [Risk Register](#risk-register)

---

## 쟁점 해결 결과

### 쟁점 1: 헬스체크 시점

| 측 | 주장 | 핵심 근거 |
|---|------|----------|
| **Dev Architect** | v2.0.0 | 진단 대상(Telegram/Discord)이 모두 갖춰진 후 구현이 완전 |
| **Product/UX** | v1.11.0 | 환경 의존성이 늘기 전에 진단 도구 선행 필요, 지원 비용 절감 |

**결정: v1.11.0에 기본 헬스체크 도입, v2.0.0에서 확장 (단계적 접근)**

**근거**:
- Product/UX의 핵심 주장이 타당하다. v1.11.0에서 주간 브리핑, sidecar 스키마 검증 등 새로운 기능이 추가되면서 환경 의존성이 복잡해진다. 사용자가 "왜 안 되지?"라고 물을 때 진단 도구가 없으면 지원 비용이 증가한다.
- 단, Dev Architect의 우려도 반영하여 v1.11.0에서는 현재 존재하는 구성요소(GA4 MCP, config.json, Python 환경, Slack webhook)만 진단한다. Telegram/Discord 진단은 v2.0.0에서 추가한다.
- 구현 복잡도가 낮다 -- config.json 읽기 + MCP 도구 존재 확인 + Python 패키지 체크 수준이므로 v1.11.0 범위 증가가 제한적이다.

**Dev Architect에 대한 보상**: v2.0.0에서 헬스체크를 확장할 때 Dev Architect가 설계한 진단 아키텍처(채널별 상태 코드, 연결 테스트 프로토콜)를 전면 적용한다. v1.11.0의 기본 버전은 v2.0.0 확장을 위한 인터페이스를 미리 정의하여, 확장 시 breaking change 없이 진행할 수 있도록 한다.

---

### 쟁점 2: 브리핑 비교(compare) 시점

| 측 | 주장 | 핵심 근거 |
|---|------|----------|
| **Dev Architect** | v1.11.0 | sidecar 활용 기능이므로 주간 요약과 같은 버전에 묶는 것이 효율적 |
| **Product/UX** | v1.12.0 | v1.11.0 범위 축소, sidecar 스키마 안정화 후 비교 기능 추가가 안전 |

**결정: v1.12.0으로 이동 (Product/UX안 채택)**

**근거**:
- v1.11.0은 이미 주간 브리핑, sidecar 스키마 정의, 헬스체크 기본판 등 범위가 크다. 여기에 비교 기능까지 추가하면 릴리스 지연 리스크가 높아진다.
- sidecar 스키마가 v1.11.0에서 정식 정의된 후 실제 데이터가 쌓이면서 스키마 결함이 발견될 수 있다. 비교 기능은 스키마에 강하게 의존하므로, 한 버전의 여유를 두는 것이 방어적 설계이다.
- v1.11.0에서 sidecar 스키마를 확정할 때 비교 기능의 요구사항을 미리 반영(diff-friendly 필드 구조)하면 v1.12.0 구현이 수월해진다.

**Dev Architect에 대한 보상**: sidecar 스키마 설계에서 비교 기능에 필요한 필드(normalized metrics, comparable keys)를 v1.11.0에 선제적으로 포함한다. 이렇게 하면 v1.12.0에서 스키마 변경 없이 비교 로직만 추가하면 되므로, Dev Architect가 우려한 "기술적 비효율"을 최소화한다.

---

### 쟁점 3: /smart-briefing:notify 커맨드

| 측 | 주장 | 핵심 근거 |
|---|------|----------|
| **Dev Architect** | 독립 커맨드 (test, status, flush). 총 8개 | 알림 시스템 전용 명령 영역 필요 |
| **Product/UX** | customize 서브옵션 흡수. 총 7개 | 인지 부하 감소, 커맨드 수 억제 |

**결정: customize 서브옵션으로 흡수, 총 7개 커맨드 유지 (Product/UX안 채택)**

**근거**:
- 현재 6개 커맨드에서 2개 추가(notify + healthcheck)하면 8개가 되는데, 이는 CLI 사용성 관점에서 과도하다. 특히 notify의 하위 동작(test, status, flush)은 "설정 관련 조작"이므로 customize의 논리적 하위 범주에 해당한다.
- `/smart-briefing:customize notification test`, `/smart-briefing:customize notification status` 형태가 직관적이다.
- 알림 시스템이 더 복잡해지는 v2.0.0 시점에서도 7개 커맨드로 충분한지 재평가할 수 있다.

**Dev Architect에 대한 보상**: customize 커맨드 내부에서 알림 관련 서브옵션을 명확히 분리된 섹션으로 구현한다. 향후 알림 복잡도가 임계점을 넘으면 독립 커맨드로 분리할 수 있도록 내부 구조를 모듈화한다. 또한 `customize notification` 서브옵션의 help 출력에서 test/status/flush 기능을 명확히 노출한다.

---

### 쟁점 4: 알림 피로도 관리

| 측 | 주장 | 핵심 근거 |
|---|------|----------|
| **Dev Architect** | 24시간 재발송 억제 (last_sent 기록). 기본 수준 | 구현 단순, 큐 파일 활용 |
| **Product/UX** | cooldown_hours, max_alerts_per_day, severity 필터링 | 실사용에서 알림 피로가 핵심 이탈 원인 |

**결정: v1.12.0에서 중간 수준, v2.0.0에서 정교한 수준 (단계적 접근)**

**근거**:
- v1.12.0(알림 시스템 도입)에서 바로 정교한 피로도 관리를 구현하면 알림 시스템 자체의 안정성 검증이 어려워진다. 기본 동작을 먼저 확인한 후 튜닝하는 것이 안전하다.
- 그러나 Dev Architect의 "24시간 하드코딩"만으로는 실사용에서 부족하다. 최소한 config.json에서 cooldown_hours를 설정 가능하게 해야 한다.

**v1.12.0 범위** (중간 수준):
- `cooldown_hours` 설정 가능 (기본값 24)
- 동일 anomaly 메트릭에 대한 재발송 억제 (last_sent 타임스탬프)
- `max_alerts_per_day` 설정 가능 (기본값 10)

**v2.0.0 범위** (정교한 수준):
- severity 기반 필터링 (critical은 항상, warning은 cooldown 적용, info는 일일 digest)
- 주간 digest 모드 (낮은 severity를 모아서 주 1회 발송)
- 알림 이력 뷰어 (`customize notification history`)

**양측 보상**: Dev Architect의 큐 파일 + last_sent 구조를 기반으로, Product/UX의 설정 항목을 config.json에 추가하는 방식. 두 접근의 장점을 단계적으로 결합한다.

---

### 쟁점 5: 브리핑 히스토리 뷰어

| 측 | 주장 | 핵심 근거 |
|---|------|----------|
| **Dev Architect** | 언급 없음 | (암묵적으로 우선순위 낮음 판단) |
| **Product/UX** | v1.11.0 또는 v1.12.0에 추가 | 구현 복잡도 낮음, 사용자 가치 중~높 |

**결정: v1.12.0에 `briefing list` 서브옵션으로 추가**

**근거**:
- v1.11.0은 이미 범위가 충분하므로 추가 부담을 주지 않는다.
- v1.12.0에서 비교 기능이 추가되는데, 비교할 대상을 탐색하려면 히스토리 뷰어가 자연스러운 전제 기능이다. "어떤 날짜와 비교할까?"를 결정하기 위해 과거 브리핑 목록을 확인하는 흐름.
- 구현은 `briefings/*.json` 파일 목록 + 각 sidecar의 요약 정보(date, preset, anomaly count) 출력 수준이므로 복잡도가 낮다.
- briefing 커맨드의 서브옵션(`briefing list` 또는 `briefing history`)으로 추가하면 커맨드 수 증가 없이 기능이 확장된다.

**Dev Architect에 대한 보상**: 히스토리 뷰어의 출력 형식을 sidecar JSON 기반으로 설계하여, 향후 CLI 파이프라인(예: `briefing list --json | jq`)과 호환되도록 한다.

---

## v1.11.0 -- Weekly Briefing & Foundation

### 목표

주간 브리핑 기능 추가, sidecar JSON 스키마 정식화, 기본 헬스체크 도입.
기존 `briefing` 커맨드의 서브옵션 확장으로 새로운 커맨드 없이 기능을 추가한다.

### 커맨드 구조 (변경 없음, 서브옵션 확장)

```
/smart-briefing:briefing              (기존) 일일 브리핑
/smart-briefing:briefing weekly       (신규) 주간 요약 브리핑
/smart-briefing:setup                 (기존)
/smart-briefing:setup healthcheck     (신규) 환경 진단
/smart-briefing:customize             (기존)
/smart-briefing:reports               (기존)
/smart-briefing:schedule              (기존)
/smart-briefing:export                (기존)
```

총 커맨드 수: **6개** (변경 없음)

### 태스크 목록

#### T1. JSON Sidecar 스키마 정의 + 검증기

**설명**: 현재 sidecar JSON은 비공식 구조로 저장되고 있다. v1.11.0에서 정식 스키마를 정의하고, 순수 Python 검증기를 구현한다.

**파일 변경**:
- `scripts/sidecar_schema.py` (신규) -- 스키마 정의 + validate() 함수
- `commands/briefing.md` -- sidecar 저장 시 검증 호출 안내 추가
- `scripts/utils.py` -- `validate_sidecar(data)` 래퍼 함수 추가

**기술적 결정**:
- jsonschema 라이브러리 미사용. 순수 Python dict 기반 검증.
- 스키마 버전 필드 포함: `"schema_version": "1.11"`
- 비교 기능 대비 diff-friendly 구조: metrics 키를 정규화된 형태로 저장
  - 모든 metric 값에 `current`, `previous`, `change_pct` 필드 보장
  - `comparable_keys` 배열 추가: 비교 가능한 메트릭 이름 목록

**스키마 정의**:
```python
SIDECAR_SCHEMA = {
    "required_fields": ["schema_version", "date", "preset", "date_range",
                        "anomaly_threshold", "metrics", "anomalies",
                        "insights", "comparable_keys"],
    "metrics_entry": {
        "required": ["current"],
        "optional": ["previous", "change_pct"]
    },
    "anomaly_entry": {
        "required": ["metric", "change_pct", "severity"]
    },
    "insight_entry": {
        "required": ["severity", "text"]
    }
}
```

**테스트 계획**:
- `tests/test_sidecar_schema.py`: 유효한 sidecar 통과, 필수 필드 누락 시 실패, 잘못된 타입 감지, 빈 metrics 허용 여부 (10+ tests)

---

#### T2. 주간 요약 브리핑 (`briefing weekly`)

**설명**: `briefing` 커맨드에 `weekly` 서브옵션을 추가. 최근 7일간의 sidecar 파일을 집계하여 주간 트렌드를 생성한다.

**파일 변경**:
- `commands/briefing.md` -- `weekly` 서브옵션 처리 섹션 추가
- `scripts/generate-charts.py` -- 주간 차트 매핑 추가 (`weekly_trend`, `weekly_comparison`)
- `scripts/manage-schedule.sh` -- `install-weekly` 액션 추가

**데이터 소스 우선순위**:
1. **1순위**: `briefings/*.json` sidecar 파일 7일 집계
2. **2순위 (fallback)**: sidecar가 부족할 경우 GA4 직접 조회 (14일 범위로 전주/이번주 비교)

**주간 브리핑 구조**:
```markdown
# 주간 GA 브리핑 - {시작일} ~ {종료일}

## 주간 핵심 요약
{7일간 전체 트렌드를 3~4문장으로 요약}

## 주간 지표 추이
| 지표 | 월 | 화 | 수 | 목 | 금 | 토 | 일 | 주간 평균 | 전주 대비 |
|------|---|---|---|---|---|---|---|----------|----------|

## 주간 이상 탐지 요약
{7일간 발생한 anomaly 집계: 빈도, 패턴}

## 주간 인사이트
{일별 인사이트 중 반복/중요 패턴 추출}

## 다음 주 주요 관찰 포인트
{데이터 기반 다음 주 주의사항}
```

**주간 차트 매핑** (generate-charts.py 추가):
| 차트 타입 | 용도 | 데이터 |
|-----------|------|--------|
| `weekly_trend` | 7일 일별 추이 라인 | sidecar metrics 시계열 |
| `weekly_comparison` | 이번주 vs 전주 비교 바 | 주간 합산 비교 |

**스케줄 연동**:
- `manage-schedule.sh install-weekly [HH:MM] [요일]` -- 기본 월요일 09:00
- macOS: 별도 launchd plist 생성
- Linux: 별도 systemd timer 생성

**테스트 계획**:
- sidecar 7일 집계 로직 단위 테스트 (정상, 부분 누락, 전체 누락 시 fallback)
- 주간 차트 데이터 매핑 테스트
- `install-weekly` 스케줄 설치/해제 테스트

---

#### T3. 기본 헬스체크 (`setup healthcheck`)

> **[쟁점 1 해결]** v1.11.0에 기본 버전 도입

**설명**: `setup` 커맨드에 `healthcheck` 서브옵션을 추가. 현재 환경의 구성 상태를 진단하고 문제를 보고한다.

**파일 변경**:
- `commands/setup.md` -- `healthcheck` 서브옵션 처리 섹션 추가
- `scripts/healthcheck.py` (신규) -- 진단 로직

**진단 항목 (v1.11.0 범위)**:
| 항목 | 점검 내용 | 상태 표시 |
|------|----------|----------|
| GA4 MCP 서버 | `get_ga4_data` 도구 사용 가능 여부 | OK / FAIL |
| config.json | 파일 존재 + JSON 유효성 + 스키마 버전 | OK / WARN / FAIL |
| Python 환경 | Python3 버전, matplotlib/weasyprint 설치 여부 | OK / WARN |
| Slack webhook | webhook_url 설정 + 연결 테스트 (HEAD 요청) | OK / SKIP / FAIL |
| sidecar 파일 | 최근 7일 sidecar 존재 여부 | OK / WARN |
| 폰트 | 한국어 폰트 탐색 결과 | OK / WARN |

**출력 형식**:
```
Smart Daily Briefing -- 환경 진단

[OK]   GA4 MCP 서버: 연결됨
[OK]   config.json: 유효 (v1.11, preset=default)
[OK]   Python 환경: 3.12.1 (homebrew)
[WARN] matplotlib: 미설치 (SVG fallback 사용)
[OK]   Slack webhook: 연결됨
[WARN] sidecar: 최근 3일만 존재 (주간 요약에 부족할 수 있음)
[OK]   한국어 폰트: NanumGothic (번들)

결과: 6/7 정상, 1 경고
```

**v2.0.0 확장 인터페이스** (v1.11.0에서 미리 정의):
```python
class HealthCheckItem:
    """v2.0.0에서 Telegram/Discord 등 새 항목 추가 시 이 인터페이스를 구현"""
    name: str
    def check(self) -> tuple[str, str]:  # (status, message)
        ...
```

**기술적 결정**:
- healthcheck.py는 독립 실행 가능한 스크립트 + 모듈 import 가능한 이중 구조
- 외부 의존성 없음 (urllib.request로 webhook 테스트)
- 종료 코드: 0=all OK, 1=warning exists, 2=fail exists

**테스트 계획**:
- 각 진단 항목의 정상/비정상 시나리오 모킹 테스트
- 출력 형식 검증
- 종료 코드 검증

---

### v1.11.0 파일 변경 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `scripts/sidecar_schema.py` | 신규 | 스키마 정의 + 검증기 |
| `scripts/healthcheck.py` | 신규 | 환경 진단 스크립트 |
| `scripts/utils.py` | 수정 | validate_sidecar 래퍼 추가 |
| `scripts/generate-charts.py` | 수정 | weekly_trend, weekly_comparison 차트 추가 |
| `scripts/manage-schedule.sh` | 수정 | install-weekly 액션 추가 |
| `commands/briefing.md` | 수정 | weekly 서브옵션, sidecar 스키마 검증 |
| `commands/setup.md` | 수정 | healthcheck 서브옵션 |
| `config.json.example` | 수정 | schema_version 필드 추가 |
| `tests/test_sidecar_schema.py` | 신규 | 스키마 검증 테스트 |
| `tests/test_healthcheck.py` | 신규 | 헬스체크 테스트 |

### v1.11.0 config.json 변경

```jsonc
{
  "version": "1.11",
  "schema_version": "1.11",
  // ... 기존 필드 유지 ...
  "weekly": {
    "schedule_day": "monday",
    "schedule_time": "09:00",
    "fallback_to_ga4": true
  }
}
```

---

## v1.12.0 -- Unified Notification System

### 목표

Python 기반 통합 알림 시스템 도입, send-slack.sh deprecation, 이상 탐지 알림 내장, 브리핑 비교 기능, 히스토리 뷰어.

### 커맨드 구조

```
/smart-briefing:briefing              일일 브리핑
/smart-briefing:briefing weekly       주간 요약 브리핑
/smart-briefing:briefing compare      (신규) 날짜 비교  [쟁점 2 해결]
/smart-briefing:briefing list         (신규) 히스토리    [쟁점 5 해결]
/smart-briefing:setup                 초기 설정
/smart-briefing:setup healthcheck     환경 진단
/smart-briefing:customize             개인화 설정
/smart-briefing:customize notification test|status|flush  (신규) [쟁점 3 해결]
/smart-briefing:reports               리포트 목록
/smart-briefing:schedule              스케줄 관리
/smart-briefing:export                PDF 내보내기
```

총 커맨드 수: **6개** (변경 없음, 서브옵션으로 확장)

### 태스크 목록

#### T4. Python 통합 알림 시스템

**설명**: `send-slack.sh`를 대체하는 Python 기반 알림 모듈. urllib.request 사용, 외부 의존성 없음.

**파일 변경**:
- `scripts/send-notification.py` (신규) -- 통합 알림 발송 엔진
- `scripts/send-slack.sh` -- deprecation wrapper로 변환 (send-notification.py 호출)
- `commands/customize.md` -- notification 서브옵션 추가
- `config.json.example` -- 알림 routing 확장

**아키텍처**:
```python
# send-notification.py 핵심 구조
class NotificationChannel(ABC):
    """채널 인터페이스 (v2.0.0에서 Telegram/Discord 추가 시 구현)"""
    def send(self, payload: dict) -> bool: ...
    def test(self) -> bool: ...

class SlackChannel(NotificationChannel): ...
# v2.0.0: class TelegramChannel(NotificationChannel): ...
# v2.0.0: class DiscordChannel(NotificationChannel): ...

class NotificationRouter:
    """config.json의 routing 설정에 따라 채널 분배"""
    def route(self, event_type: str, payload: dict): ...
```

**send-slack.sh deprecation**:
```bash
#!/bin/bash
# DEPRECATED: send-notification.py를 사용하세요.
# 이 스크립트는 호환성을 위해 send-notification.py를 호출합니다.
echo "WARNING: send-slack.sh is deprecated. Use send-notification.py instead." >&2
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/send-notification.py" --channel slack "$@"
```

**customize notification 서브옵션** [쟁점 3 해결]:
```
/smart-briefing:customize notification test     -- 설정된 채널에 테스트 메시지 발송
/smart-briefing:customize notification status   -- 채널별 연결 상태 + 큐 상태
/smart-briefing:customize notification flush    -- 실패 큐 재발송
```

**기술적 결정**:
- 큐 파일 형식 유지 (`notification-queue.json`), Python에서 직접 읽기/쓰기
- send-slack.sh는 v2.0.0까지 유지 (deprecation warning 출력 + 동일 기능 보장)
- 재시도 로직: exponential backoff (1s, 2s, 4s), 최대 3회

**테스트 계획**:
- SlackChannel.send() 성공/실패 모킹 테스트
- NotificationRouter 라우팅 로직 테스트
- 큐 파일 읽기/쓰기/플러시 테스트
- deprecation wrapper 호환성 테스트

---

#### T5. 이상 탐지 즉시 알림

**설명**: 브리핑 파이프라인 내에서 anomaly 발견 시 알림을 발송한다. 독립 스케줄이 아닌 브리핑 생성 과정에 내장.

**파일 변경**:
- `commands/briefing.md` -- 이상 탐지 후 알림 발송 단계 추가
- `scripts/send-notification.py` -- anomaly 전용 페이로드 포맷
- `config.json.example` -- 알림 피로도 관리 설정 추가

**알림 피로도 관리** [쟁점 4 해결 -- v1.12.0 범위]:
```jsonc
{
  "notifications": {
    "slack": {
      "webhook_url": "...",
      "enabled": true
    },
    "anomaly_alerts": {
      "enabled": true,
      "cooldown_hours": 24,        // 동일 메트릭 재발송 억제 시간 (기본 24)
      "max_alerts_per_day": 10     // 일일 최대 알림 수 (기본 10)
    }
  }
}
```

**피로도 관리 동작**:
1. anomaly 발견 시 `briefings/.alert-history.json`에서 해당 메트릭의 `last_sent` 확인
2. `cooldown_hours` 이내면 발송 억제
3. 오늘 발송 횟수가 `max_alerts_per_day` 이상이면 발송 억제
4. 억제된 알림은 로그에 기록 (`"suppressed: cooldown"` / `"suppressed: daily_limit"`)

**기술적 결정**:
- alert-history.json 구조: `{"metric_name": {"last_sent": "ISO8601", "count_today": N}}`
- 브리핑 파이프라인에 내장 = 별도 cron 불필요
- severity 기반 필터링은 v2.0.0으로 미룸

**테스트 계획**:
- cooldown 시간 내 동일 메트릭 재발송 억제 확인
- max_alerts_per_day 도달 시 억제 확인
- alert-history.json 만료/정리 로직 테스트

---

#### T6. 브리핑 비교 (`briefing compare`)

> **[쟁점 2 해결]** v1.12.0으로 이동

**설명**: 두 날짜의 sidecar JSON을 비교하여 변화를 분석한다.

**파일 변경**:
- `commands/briefing.md` -- `compare` 서브옵션 처리 섹션 추가

**사용법**:
```
/smart-briefing:briefing compare              -- 어제 vs 오늘 (기본)
/smart-briefing:briefing compare 2026-02-20   -- 해당 날짜 vs 오늘
/smart-briefing:briefing compare 2026-02-18 2026-02-25  -- 두 날짜 비교
```

**비교 출력 구조**:
```markdown
# 브리핑 비교: 2026-02-18 vs 2026-02-25

## 지표 변화
| 지표 | 2/18 | 2/25 | 변화 |
|------|------|------|------|
| sessions | 7,500 | 8,200 | +9.3% |

## 새로 발생한 이상 탐지
- averageSessionDuration: 2/18에는 정상, 2/25에 warning (+22.4%)

## 해소된 이상 탐지
- (없음)

## 트래픽 소스 변동
- google/organic: 45.2% -> 48.1% (+2.9%p)
```

**기술적 결정**:
- v1.11.0에서 정의한 `comparable_keys` 배열 활용
- sidecar가 없는 날짜는 에러 메시지 + `briefing list`로 안내
- 비교 결과도 JSON으로 저장: `briefings/compare-{date1}-vs-{date2}.json`

**테스트 계획**:
- 정상 비교 출력 검증
- sidecar 누락 시 에러 처리
- 동일 날짜 비교 시 안내 메시지

---

#### T7. 브리핑 히스토리 뷰어 (`briefing list`)

> **[쟁점 5 해결]** v1.12.0에 추가

**설명**: 과거 브리핑 목록을 조회한다.

**파일 변경**:
- `commands/briefing.md` -- `list` 서브옵션 처리 섹션 추가

**사용법**:
```
/smart-briefing:briefing list         -- 최근 14일 (기본)
/smart-briefing:briefing list 30      -- 최근 30일
/smart-briefing:briefing list all     -- 전체
```

**출력 형식**:
```
저장된 브리핑 목록 (최근 14일):

| 날짜 | 프리셋 | 이상 탐지 | 인사이트 | PDF | 주간 |
|------|--------|----------|---------|-----|------|
| 2026-02-25 | default | 1 warning | 5 | O | - |
| 2026-02-24 | campaign | 0 | 4 | O | - |
| 2026-02-23 | default | 2 critical | 5 | X | - |
| 2026-02-17 | default | - | - | - | O (주간) |

총 12개 브리핑 (일일 11, 주간 1)
비교: /smart-briefing:briefing compare {날짜}
```

**기술적 결정**:
- `briefings/*.json` glob으로 파일 목록 수집
- 각 sidecar에서 date, preset, anomalies 수, insights 수 추출
- PDF 존재 여부: 같은 날짜의 `.pdf` 파일 확인
- 주간 브리핑: 파일명 `weekly-*.json` 패턴으로 구분
- `--json` 플래그로 JSON 출력 지원 (향후 파이프라인 호환)

**테스트 계획**:
- 빈 디렉토리 시 안내 메시지
- 날짜 범위 필터링 검증
- sidecar 파일 파싱 실패 시 graceful 처리

---

### v1.12.0 파일 변경 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `scripts/send-notification.py` | 신규 | Python 통합 알림 엔진 |
| `scripts/send-slack.sh` | 수정 | deprecation wrapper로 변환 |
| `commands/briefing.md` | 수정 | compare, list 서브옵션, 이상 탐지 알림 |
| `commands/customize.md` | 수정 | notification test/status/flush 서브옵션 |
| `config.json.example` | 수정 | anomaly_alerts 섹션, 알림 routing |
| `tests/test_notification.py` | 신규 | 알림 시스템 테스트 |
| `tests/test_compare.py` | 신규 | 비교 기능 테스트 |

### v1.12.0 config.json 변경

```jsonc
{
  "version": "1.12",
  "schema_version": "1.11",   // sidecar 스키마는 변경 없음
  // ... 기존 필드 유지 ...
  "notifications": {
    "slack": {
      "webhook_url": "",
      "enabled": false
    },
    "anomaly_alerts": {
      "enabled": false,
      "cooldown_hours": 24,
      "max_alerts_per_day": 10
    },
    "routing": {
      "briefing": ["slack"],
      "anomaly": ["slack"],
      "report": ["slack"]
    }
  }
}
```

---

## v2.0.0 -- Multi-Channel & Major Upgrade

### 목표

Telegram/Discord 완전 지원, config.json v2.0 마이그레이션, send-slack.sh 완전 제거, 정교한 알림 피로도 관리, 헬스체크 확장, requirements.txt 도입.

### Breaking Changes

| 항목 | 변경 내용 | 마이그레이션 |
|------|----------|------------|
| config.json | version "2.0" + 새 스키마 | 자동 마이그레이션 스크립트 (원본 .bak 백업) |
| send-slack.sh | 완전 삭제 | send-notification.py로 대체 (v1.12.0에서 이미 wrapper) |
| Python 의존성 | requirements.txt 도입 | 기존 auto_install 유지, 선택적 pip install -r |

### 커맨드 구조 (최종)

```
/smart-briefing:briefing              일일 브리핑
/smart-briefing:briefing weekly       주간 요약 브리핑
/smart-briefing:briefing compare      날짜 비교
/smart-briefing:briefing list         히스토리 조회
/smart-briefing:setup                 초기 설정
/smart-briefing:setup healthcheck     환경 진단 (확장: Telegram/Discord 포함)
/smart-briefing:customize             개인화 설정
/smart-briefing:customize notification test|status|flush|history  알림 관리
/smart-briefing:reports               리포트 목록
/smart-briefing:schedule              스케줄 관리
/smart-briefing:export                PDF 내보내기
```

총 커맨드 수: **6개** (변경 없음) + 기존 커맨드 이름 변경 없음

### 태스크 목록

#### T8. Telegram/Discord 채널 완전 지원

**파일 변경**:
- `scripts/send-notification.py` -- TelegramChannel, DiscordChannel 클래스 추가
- `config.json.example` -- telegram, discord 섹션 추가

**config.json 알림 구조 (v2.0)**:
```jsonc
{
  "notifications": {
    "slack": {
      "webhook_url": "",
      "enabled": false
    },
    "telegram": {
      "bot_token": "",
      "chat_id": "",
      "enabled": false
    },
    "discord": {
      "webhook_url": "",
      "enabled": false
    },
    "anomaly_alerts": {
      "enabled": false,
      "cooldown_hours": 24,
      "max_alerts_per_day": 10,
      "severity_filter": "warning",
      "digest_mode": {
        "enabled": false,
        "schedule": "weekly",
        "day": "monday",
        "time": "09:00"
      }
    },
    "routing": {
      "briefing": ["slack", "telegram"],
      "anomaly": ["slack", "discord"],
      "report": ["slack"],
      "weekly": ["slack", "telegram"],
      "digest": ["slack"]
    }
  }
}
```

**기술적 결정**:
- Telegram: Bot API (urllib.request, `https://api.telegram.org/bot{token}/sendMessage`)
- Discord: Webhook API (urllib.request, embed 형식)
- 모든 채널에 동일한 재시도/큐 로직 적용

---

#### T9. 정교한 알림 피로도 관리

> **[쟁점 4 해결 -- v2.0.0 범위]**

**파일 변경**:
- `scripts/send-notification.py` -- severity 필터링, digest 모드 추가
- `config.json.example` -- severity_filter, digest_mode 추가

**기능**:
- severity 기반 필터링:
  - `critical`: 항상 즉시 발송 (cooldown 무시)
  - `warning`: cooldown_hours 적용
  - `info`: digest 모드 활성화 시 모아서 발송, 비활성화 시 발송 억제
- 주간 digest 모드: 낮은 severity 알림을 모아서 주 1회 요약 발송
- 알림 이력 뷰어: `customize notification history` -- 최근 30일 발송/억제 이력

---

#### T10. config.json v2.0 자동 마이그레이션

**파일 변경**:
- `scripts/migrate-config.py` (신규) -- v1.x -> v2.0 마이그레이션

**마이그레이션 규칙**:
```
v1.0 -> v2.0:
  - version: "1.0" -> "2.0"
  - notifications 섹션 구조 변경
  - schema_version이 없으면 추가
  - weekly 섹션이 없으면 기본값 추가
  - anomaly_alerts가 없으면 기본값 추가
  - routing이 없으면 기존 slack 설정 기반 자동 생성

v1.11 -> v2.0:
  - version: "1.11" -> "2.0"
  - anomaly_alerts 확장 필드 추가

v1.12 -> v2.0:
  - version: "1.12" -> "2.0"
  - 최소 변경 (구조 동일, severity_filter + digest_mode 추가)
```

**안전장치**:
- 마이그레이션 전 `config.json.bak` 자동 백업
- dry-run 모드 지원 (`--dry-run`): 변경 사항만 출력
- 마이그레이션 실패 시 원본 유지 + 에러 메시지

---

#### T11. send-slack.sh 완전 제거

**파일 변경**:
- `scripts/send-slack.sh` -- 삭제
- `scripts/manage-schedule.sh` -- send-slack.sh 참조를 send-notification.py로 교체
- `commands/schedule.md` -- 안내 텍스트 업데이트

---

#### T12. 헬스체크 확장

> **[쟁점 1 해결 -- v2.0.0 확장]**

**파일 변경**:
- `scripts/healthcheck.py` -- Telegram/Discord 진단 항목 추가

**추가 진단 항목**:
| 항목 | 점검 내용 |
|------|----------|
| Telegram Bot | bot_token 유효성 + getMe API 호출 |
| Discord Webhook | webhook_url 유효성 + HEAD 요청 |
| config.json v2.0 | 마이그레이션 완료 여부 |
| requirements.txt | 필수 패키지 설치 상태 |

---

#### T13. requirements.txt 도입

**파일 변경**:
- `requirements.txt` (신규)

**내용**:
```
# Smart Daily Briefing - Python Dependencies
# 핵심 기능은 외부 의존성 없이 동작합니다.
# 아래 패키지는 선택적이며, 없으면 fallback이 동작합니다.

# 차트 생성 (없으면 SVG fallback)
matplotlib>=3.7

# PDF 생성 (없으면 PDF 건너뜀)
weasyprint>=60
markdown>=3.4
```

**기술적 결정**:
- 모든 패키지는 optional. requirements.txt는 편의를 위한 것.
- 기존 auto_install 로직은 유지 (requirements.txt 없이도 동작)
- setup 커맨드에서 `pip install -r requirements.txt` 안내 추가

---

### v2.0.0 파일 변경 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `scripts/send-notification.py` | 수정 | Telegram/Discord 채널, severity 필터, digest |
| `scripts/send-slack.sh` | 삭제 | 완전 제거 |
| `scripts/migrate-config.py` | 신규 | config.json 자동 마이그레이션 |
| `scripts/healthcheck.py` | 수정 | Telegram/Discord/config v2 진단 추가 |
| `scripts/manage-schedule.sh` | 수정 | send-slack.sh 참조 제거 |
| `commands/setup.md` | 수정 | requirements.txt 안내, 마이그레이션 안내 |
| `commands/customize.md` | 수정 | notification history 서브옵션 |
| `commands/schedule.md` | 수정 | send-slack.sh 참조 제거 |
| `config.json.example` | 수정 | v2.0 전체 스키마 |
| `requirements.txt` | 신규 | Python 의존성 목록 |
| `tests/test_migration.py` | 신규 | 마이그레이션 테스트 |
| `tests/test_telegram.py` | 신규 | Telegram 채널 테스트 |
| `tests/test_discord.py` | 신규 | Discord 채널 테스트 |
| `tests/test_severity_filter.py` | 신규 | 피로도 관리 테스트 |

---

## Timeline Summary

```
v1.10.0 (현재)
    |
    |  [T1] sidecar 스키마 정의 + 검증기
    |  [T2] 주간 요약 브리핑 (briefing weekly)
    |  [T3] 기본 헬스체크 (setup healthcheck)        ← 쟁점 1 해결
    |
v1.11.0
    |
    |  [T4] Python 통합 알림 시스템
    |  [T5] 이상 탐지 즉시 알림 + 중간 수준 피로도    ← 쟁점 4 (중간)
    |  [T6] 브리핑 비교 (briefing compare)            ← 쟁점 2 해결
    |  [T7] 브리핑 히스토리 (briefing list)            ← 쟁점 5 해결
    |       customize notification test/status/flush   ← 쟁점 3 해결
    |
v1.12.0
    |
    |  [T8]  Telegram/Discord 완전 지원
    |  [T9]  정교한 알림 피로도 (severity, digest)     ← 쟁점 4 (완성)
    |  [T10] config.json v2.0 자동 마이그레이션
    |  [T11] send-slack.sh 완전 제거
    |  [T12] 헬스체크 확장                            ← 쟁점 1 (완성)
    |  [T13] requirements.txt 도입
    |
v2.0.0
```

### 쟁점별 해결 시점 요약

| 쟁점 | 결정 | 적용 버전 |
|------|------|----------|
| 쟁점 1: 헬스체크 | 기본판 선행 + v2.0 확장 | v1.11.0 (기본) + v2.0.0 (확장) |
| 쟁점 2: 브리핑 비교 | v1.12.0으로 이동 | v1.12.0 |
| 쟁점 3: notify 커맨드 | customize 서브옵션 흡수 | v1.12.0 |
| 쟁점 4: 알림 피로도 | 중간 수준 -> 정교한 수준 | v1.12.0 (중간) + v2.0.0 (정교) |
| 쟁점 5: 히스토리 뷰어 | briefing list 서브옵션 | v1.12.0 |

### 버전별 커맨드 수 추이

| 버전 | 최상위 커맨드 | 서브옵션 (신규) | 총 진입점 |
|------|-------------|---------------|----------|
| v1.10.0 (현재) | 6 | 0 | 6 |
| v1.11.0 | 6 | +2 (weekly, healthcheck) | 8 |
| v1.12.0 | 6 | +5 (compare, list, notification test/status/flush) | 13 |
| v2.0.0 | 6 | +1 (notification history) | 14 |

---

## Risk Register

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| v1.11.0 범위 과대 (주간+스키마+헬스체크) | 릴리스 지연 | 헬스체크를 최소 기능으로 제한, 스키마 검증은 warning 수준으로 시작 |
| sidecar 스키마 v1.11.0에서 결함 발견 | v1.12.0 비교 기능에 영향 | comparable_keys 등 확장 필드를 optional로 설계, 스키마 버전 관리 |
| send-slack.sh deprecation 기간 부족 | 기존 사용자 혼란 | v1.12.0에서 deprecation warning 시작, v2.0.0까지 1개 마이너 버전 유예 |
| config.json v2.0 마이그레이션 실패 | 설정 유실 | 원본 .bak 백업 필수, dry-run 모드, 실패 시 원본 유지 |
| Telegram/Discord API 변경 | v2.0.0 채널 구현 무효화 | 채널 인터페이스 추상화로 개별 채널 교체 용이 |
| 알림 피로도 설정 복잡도 | 사용자 설정 포기 | 합리적 기본값 제공, customize show에서 현재 상태 명확히 표시 |

---

## Test Count Projection

| 버전 | 신규 테스트 | 누적 총 테스트 |
|------|-----------|-------------|
| v1.10.0 (현재) | - | 41 |
| v1.11.0 | ~25 (sidecar 10 + 주간집계 8 + 헬스체크 7) | ~66 |
| v1.12.0 | ~30 (알림 12 + 비교 8 + 히스토리 4 + 피로도 6) | ~96 |
| v2.0.0 | ~40 (Telegram 10 + Discord 10 + 마이그레이션 8 + severity 7 + requirements 5) | ~136 |
