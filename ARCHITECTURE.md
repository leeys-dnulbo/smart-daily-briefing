# Architecture - Smart Daily Briefing

플러그인의 핵심 구조와 데이터 흐름을 설명합니다.

---

## 시스템 전체 구조

```mermaid
graph TB
    User([사용자])

    subgraph Plugin["Smart Daily Briefing Plugin"]
        subgraph Triggers["입력 계층"]
            Skills["Skills<br/><small>자연어 자동 트리거</small>"]
            Commands["Commands<br/><small>슬래시 커맨드</small>"]
        end

        subgraph Core["처리 계층"]
            Config["config.json<br/><small>개인화 설정</small>"]
            Scripts["Scripts<br/><small>차트/PDF 생성</small>"]
            Hooks["Hooks<br/><small>환경변수, 유효성</small>"]
        end

        subgraph Output["출력 계층"]
            MD["briefings/*.md"]
            JSON["briefings/*.json<br/><small>sidecar 구조화 데이터</small>"]
            PDF["briefings/*.pdf"]
            Charts["briefings/charts/"]
            Reports["reports/*.json"]
        end
    end

    MCP["GA4 MCP Server<br/><small>google-analytics-mcp</small>"]
    GA4["Google Analytics<br/>Data API"]
    Slack["Slack Webhook"]
    Telegram["Telegram Bot API"]
    Discord["Discord Webhook"]

    User --> Skills
    User --> Commands
    Skills --> MCP
    Commands --> MCP
    Commands --> Config
    Commands --> Scripts
    MCP --> GA4
    Scripts --> Charts
    Scripts --> PDF
    Commands --> MD
    Commands --> Reports
    Hooks -.->|환경변수 주입| Scripts
    Hooks -.->|코드 검증| Commands
    Commands -.-> Slack
    Commands -.-> Telegram
    Commands -.-> Discord
```

---

## 브리핑 생성 파이프라인

`/smart-briefing:briefing` 실행 시 전체 흐름입니다.

```mermaid
flowchart LR
    A[config.json 로드] --> B[활성 섹션 필터]
    B --> C[GA4 데이터 수집<br/><small>섹션별 get_ga4_data</small>]
    C --> D[전주 비교 데이터]
    D --> E[이상 탐지<br/><small>±20% 기준</small>]
    E --> F[차트 이미지 생성<br/><small>generate-charts.py</small>]
    F --> G[마크다운 조합]
    G --> H[briefings/YYYY-MM-DD.md<br/>저장]
    H --> I[PDF 자동 생성<br/><small>generate-pdf.py</small>]
    I --> J[briefings/YYYY-MM-DD.pdf<br/>저장]
```

### 브리핑 섹션 구성

```mermaid
graph LR
    subgraph Default["기본 활성 (5개)"]
        S1["핵심 지표<br/>오버뷰"]
        S2["상위 페이지"]
        S3["트래픽 소스"]
        S4["일별 트렌드"]
        S5["디바이스별"]
    end

    subgraph Optional["선택 활성 (4개)"]
        S6["캠페인 성과"]
        S7["이벤트 분석"]
        S8["랜딩 페이지"]
        S9["사용자 행동패턴"]
    end

    Config["config.json<br/>preset / sections"] --> Default
    Config --> Optional
```

---

## 차트 생성 로직

```mermaid
flowchart TB
    Start[차트 데이터 입력] --> CheckMPL{matplotlib<br/>설치?}

    CheckMPL -->|Yes| Font[폰트 탐색]
    CheckMPL -->|No| SVG[SVG fallback<br/><small>순수 Python</small>]

    Font --> F1{번들 폰트<br/>fonts/NanumGothic?}
    F1 -->|있음| UseBundled[번들 폰트 사용]
    F1 -->|없음| F2{시스템 폰트?}
    F2 -->|있음| UseSys[시스템 폰트 사용]
    F2 -->|없음| F3{fc-list?}
    F3 -->|있음| UseFC[fc-list 폰트 사용]
    F3 -->|없음| Fallback[이름 기반 fallback]

    UseBundled --> Render
    UseSys --> Render
    UseFC --> Render
    Fallback --> Render

    Render[FontProperties 직접 적용<br/><small>모든 Text 객체</small>]
    Render --> PNG["PNG 차트 출력"]

    SVG --> SVGOUT["SVG 차트 출력"]

    PNG --> Done[차트 파일 저장]
    SVGOUT --> Done
```

### 차트 종류

| 타입 | 용도 | 섹션 |
|------|------|------|
| `daily_trend` | 일별 추이 (bar+line 복합) | 일별 트렌드, 주간 일별 추이 |
| `horizontal_bar` | 수평 막대 (Top N) | 상위 페이지, 트래픽 소스, 랜딩 페이지, 캠페인, 이벤트 |
| `pie` / 도넛 | 비율 차트 | 디바이스별 |
| `change_bar` | 전주 대비 변화율 | 핵심 지표, 사용자 행동패턴, 주간 비교 |

---

## 훅 시스템

```mermaid
sequenceDiagram
    participant U as 사용자
    participant CC as Claude Code
    participant H1 as inject-plugin-root.sh
    participant H2 as validate-chart-code.py
    participant S as Scripts

    Note over CC,H1: SessionStart 훅
    CC->>H1: 세션 시작
    H1->>CC: $SMART_BRIEFING_ROOT 설정

    Note over U,S: Bash 도구 호출 시
    U->>CC: /smart-briefing:briefing
    CC->>H2: PreToolUse (Bash 코드 검사)
    alt matplotlib/weasyprint 직접 사용
        H2-->>CC: DENY (스크립트 사용 안내)
    else 정상 스크립트 호출
        H2-->>CC: ALLOW
        CC->>S: $SMART_BRIEFING_ROOT/scripts/generate-charts.py
    end
```

| 훅 | 이벤트 | 역할 |
|-----|--------|------|
| `inject-plugin-root.sh` | SessionStart | `$SMART_BRIEFING_ROOT` 환경변수 주입 |
| `validate-chart-code.py` | PreToolUse (Bash) | matplotlib/weasyprint 직접 코드 차단 |

---

## PDF 생성 파이프라인

```mermaid
flowchart LR
    MD["briefings/YYYY-MM-DD.md"] --> Parse[마크다운 파싱<br/><small>markdown 라이브러리</small>]
    Parse --> HTML[HTML 변환<br/><small>tables, fenced_code</small>]
    HTML --> Img[이미지 경로 변환<br/><small>상대 → file:// 절대</small>]
    Img --> Template["HTML 템플릿 래핑<br/><small>A4, 한국어 폰트, 페이지 번호</small>"]
    Template --> WP[weasyprint<br/>HTML → PDF]
    WP --> PDF["briefings/YYYY-MM-DD.pdf"]
```

---

## 설정 시스템

```mermaid
graph TB
    subgraph Presets["프리셋 (5종)"]
        P1["default<br/><small>overview, pages,<br/>traffic, trend, device</small>"]
        P2["behavior<br/><small>overview, user_behavior,<br/>top_pages, events, trend</small>"]
        P3["traffic<br/><small>overview, traffic_sources,<br/>landing_pages, trend, device</small>"]
        P4["campaign<br/><small>overview, campaigns,<br/>traffic_sources, landing_pages, trend</small>"]
        P5["content<br/><small>overview, top_pages,<br/>landing_pages, events, trend</small>"]
    end

    Config["config.json"]
    Briefing["브리핑 생성"]

    Presets -->|프리셋 적용| Config
    Config -->|sections, date_range,<br/>anomaly_threshold| Briefing
    Config -->|export.auto_pdf| PDF[PDF 자동 생성]
    Config -->|notifications.*| Notify[멀티채널 알림<br/><small>Slack/Telegram/Discord</small>]
```

### 주요 설정 항목

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `briefing.date_range` | `7daysAgo` | 데이터 조회 기간 |
| `briefing.anomaly_threshold` | `20` | 이상 탐지 임계값 (%) |
| `briefing.max_insights` | `5` | 인사이트 최대 수 |
| `briefing.max_actions` | `4` | 액션 아이템 최대 수 |
| `export.auto_pdf` | `true` | 브리핑 시 PDF 자동 생성 |
| `notifications.slack.enabled` | `false` | Slack 알림 활성화 |
| `notifications.telegram.enabled` | `false` | Telegram 알림 활성화 |
| `notifications.discord.enabled` | `false` | Discord 알림 활성화 |
| `notifications.anomaly_alerts.enabled` | `true` | 이상 탐지 자동 알림 |
| `notifications.anomaly_alerts.cooldown_hours` | `4` | 동일 메트릭 알림 간격 |
| `notifications.anomaly_alerts.max_alerts_per_day` | `10` | 일일 최대 알림 수 |

---

## 플랫폼 분기

```mermaid
graph TB
    User([사용자 요청])

    User --> Detect{실행 환경?}

    Detect -->|Claude Code| CC[슬래시 커맨드<br/><small>/smart-briefing:briefing</small>]
    Detect -->|OpenClaw| OC[자연어 스킬<br/><small>"브리핑 생성해줘"</small>]
    Detect -->|Cowork| CW[자연어 요청<br/><small>CLAUDE.md 자동 로드</small>]

    CC --> Core[공통 로직<br/><small>GA4 조회 → 분석 → 저장</small>]
    OC --> Core
    CW --> Core

    Core --> Schedule{스케줄링?}

    Schedule -->|Claude Code| Launchd[macOS launchd<br/><small>manage-schedule.sh</small>]
    Schedule -->|OpenClaw| Cron[OpenClaw cron<br/><small>크로스 플랫폼</small>]
    Schedule -->|Cowork| CoworkSched[Cowork /schedule<br/><small>앱 실행 중 자동</small>]
```

---

## 스크립트 경로 탐색

`$SMART_BRIEFING_ROOT`가 SessionStart 훅으로 자동 설정되며, fallback 체인으로 스크립트를 찾습니다.

```mermaid
flowchart TB
    A{$SMART_BRIEFING_ROOT<br/>설정됨?}
    A -->|Yes| B["$SMART_BRIEFING_ROOT/scripts/generate-charts.py"]
    A -->|No| C["find로 검색<br/><small>~/.claude, ~/Library/...</small>"]
    C --> D{찾음?}
    D -->|Yes| E[검색된 경로 사용]
    D -->|No| F["scripts/generate-charts.py<br/><small>현재 디렉토리 fallback</small>"]
```

---

## v1.10.0 아키텍처 변경사항

### scripts/utils.py (공통 유틸리티)

`generate-charts.py`와 `generate-pdf.py`에서 중복된 코드를 추출한 공유 모듈:

| 함수 | 역할 |
|------|------|
| `ensure_best_python(test_import)` | homebrew Python 우선 자동 전환 |
| `auto_install(*packages)` | pip 자동 설치 (2회 시도) |
| `find_korean_font()` | 한국어 폰트 탐색 (번들 → 시스템 → fc-list) |
| `safe_write(path, data)` | atomic write (tempfile → os.replace) |
| `safe_write_json(path, obj)` | JSON atomic write |

### JSON sidecar 저장

브리핑 생성 시 `briefings/YYYY-MM-DD.json` 파일을 함께 생성합니다.
구조화된 metrics, anomalies, insights를 저장하여 향후 비교/주간 기능의 데이터 소스로 활용합니다.

### AST 기반 코드 검증 (validate-chart-code.py)

기존 regex denylist 방식에서 `ast.NodeVisitor` 기반 whitelist 방식으로 재작성:
- `visit_Import`, `visit_ImportFrom`: 직접 import 차단
- `visit_Call`: `__import__()`, `importlib.import_module()`, `eval()`, `exec()` 차단
- `visit_Constant`: 인코딩된 바이트 리터럴 차단
- 비-Python 코드는 text fallback 검사

### 테스트 프레임워크

`tests/` 디렉토리에 pytest 기반 테스트:
- `test_utils.py`: safe_write, 폰트 검색, auto_install (17 tests)
- `test_validate_chart_code.py`: AST 검증 차단/허용/엣지케이스 (18 tests)

---

## v1.11.0 아키텍처 변경사항

### JSON sidecar 스키마 v1.11 (sidecar_schema.py)

순수 Python 검증기. `jsonschema` 의존성 없이 동작:

| 함수 | 역할 |
|------|------|
| `validate_sidecar(data)` | 스키마 검증 (CRITICAL vs 권장 필드 구분) |
| `normalize_sidecar(data)` | v1.10.0 sidecar를 v1.11 형식으로 정규화 |
| `aggregate_sidecars(sidecars)` | 일별 sidecar를 주간 단위로 집계 (SUM/가중평균) |

스키마에 `schema_version`, `comparable_keys` 필드 추가. 비교 기능의 데이터 소스.

### 주간 브리핑 파이프라인

```
W1: 주간 범위 결정 (월~일 또는 지정 날짜 기준)
W2: sidecar 수집 (4/7 이상 → 집계 / 미만 → GA4 fallback)
W3: 차트 생성 (weekly_trend, weekly_comparison)
W4: 마크다운 생성 (briefings/weekly-YYYY-MM-DD.md)
W5: PDF 자동 생성 (설정에 따라)
```

차트 생성 시 기존 핸들러(`daily_trend`, `overview_change`)를 재사용하여 코드 중복을 방지.

### 환경 진단 (healthcheck.py)

`HealthCheckItem` 기반 확장 가능한 진단 시스템 (12개 항목):

| 항목 | key | 진단 대상 |
|------|-----|-----------|
| config.json | `config` | 설정 파일 유효성 |
| Python 환경 | `python` | 버전 ≥ 3.9 |
| matplotlib | `matplotlib` | 차트 라이브러리 |
| weasyprint | `weasyprint` | PDF 라이브러리 |
| Slack webhook | `slack` | 연결 테스트 |
| Telegram Bot | `telegram` | getMe API 토큰 검증 |
| Discord webhook | `discord` | webhook URL 유효성 |
| config 버전 | `config_version` | v2.0 마이그레이션 확인 |
| sidecar 파일 | `sidecar` | 최근 7일 존재 여부 |
| 한국어 폰트 | `font` | 폰트 탐색 |
| 필수 스크립트 | `scripts` | 6개 스크립트 존재 |
| 네트워크 프록시 | `proxy` | 컨테이너 환경 프록시 상태 |

CLI: `python3 scripts/healthcheck.py [--json] [--check key1,key2]`
모듈: `run_healthcheck(plugin_dir, checks)` → `[(key, name, status, message)]`

---

## v1.12.0 아키텍처 변경사항

### Python 통합 알림 시스템 (send-notification.py)

순수 Python 구현의 멀티채널 알림 시스템. 채널 추상화 패턴:

```
NotificationChannel (base)
├── SlackChannel — Incoming Webhook
├── TelegramChannel — Bot API (sendMessage)
└── DiscordChannel — Webhook (embed 형식)
```

| 함수 | 역할 |
|------|------|
| `send_with_retry(ch, payload, config)` | 지수 백오프 재시도 (최대 3회) |
| `enqueue(type, payload, channel)` | 실패 메시지 JSON 큐 저장 (채널 메타데이터 포함) |
| `flush_queue(config)` | 큐 재전송 (채널별 라우팅) |
| `get_active_channels(config)` | 활성 채널 목록 조회 |

CLI: `python3 scripts/send-notification.py <briefing|test|anomaly|flush|status> [args]`

### 이상 탐지 모니터 (anomaly-monitor.py)

브리핑 sidecar에서 이상 탐지를 추출하고 쿨다운/한도를 적용하여 알림 전송:

```
sidecar.json → extract anomalies → filter (cooldown/limit/severity) → send-notification.py anomaly
                                                                    → .alert-history.json 기록
```

| 기능 | 설명 |
|------|------|
| 쿨다운 | 동일 메트릭 재알림 간격 (기본 4시간) |
| 일일 한도 | 하루 최대 알림 수 (기본 10건) |
| 심각도 필터 | min_severity 이상만 알림 |
| 히스토리 | `.alert-history.json`에 7일간 보관 |

### 브리핑 비교 (briefing compare)

두 날짜의 sidecar JSON을 비교하여 지표 변화를 분석:

```
C1: 비교 대상 결정 (어제 vs 그제 또는 지정 날짜)
C2: sidecar 로드 (comparable_keys 합집합)
C3: 변화율 계산 ((이후-이전)/이전 × 100)
C4: 비교 결과 출력 (터미널만, 파일 저장 없음)
```

### 브리핑 히스토리 (briefing list)

최근 14일 `briefings/` 디렉토리의 .md, .json, .pdf 파일을 탐색하여 목록 출력.

---

## v2.0.0 아키텍처 변경사항

### 멀티채널 알림 시스템

Slack 단일 채널에서 Telegram/Discord를 추가한 3채널 동시 지원:

```mermaid
flowchart LR
    Event["이벤트 발생<br/><small>briefing/anomaly/test</small>"]
    Event --> Router["get_active_channels()"]
    Router --> Slack["SlackChannel<br/><small>Incoming Webhook</small>"]
    Router --> Telegram["TelegramChannel<br/><small>Bot API sendMessage</small>"]
    Router --> Discord["DiscordChannel<br/><small>Webhook embed</small>"]
    Slack -->|실패| Queue["notification-queue.json<br/><small>channel 메타데이터 포함</small>"]
    Telegram -->|실패| Queue
    Discord -->|실패| Queue
    Queue -->|flush| Router
```

채널별 특징:

| 채널 | 프로토콜 | 메시지 제한 | 성공 응답 |
|------|---------|-----------|----------|
| Slack | POST → webhook URL | text 필드 | 200 + "ok" |
| Telegram | POST → Bot API | 4096자 | 200 + `{"ok": true}` |
| Discord | POST → webhook URL | embed field 1024자 | 200 또는 204 |

### 알림 큐 v2.0

큐 엔트리에 `channel` 필드 추가. v1.12 큐와 하위 호환 (`entry.get("channel", "slack")`):

```json
{
  "type": "briefing",
  "payload": {"text": "..."},
  "channel": "telegram",
  "timestamp": "2026-02-26T09:00:00",
  "retries": 0
}
```

### 커맨드 구조 정리

| 변경 | 상세 |
|------|------|
| `notification` 커맨드 신규 | customize에서 알림 관련 기능 분리 |
| `export` → `briefing export` 흡수 | export 커맨드는 deprecation wrapper로 유지 |
| `customize` 경량화 | 알림 상태는 한 줄 요약만, 상세는 notification 안내 |

### Config v2.0 마이그레이션

`scripts/migrate-config.py`로 v1.x → v2.0 자동 마이그레이션:
- `telegram`, `discord` 섹션 추가 (disabled 기본값)
- `version` → `"2.0"` 업데이트
- `config.json.bak` 자동 백업
- `--dry-run` 플래그 지원, 멱등성 보장

### send-slack.sh 완전 제거

`send-slack.sh`를 삭제하고 모든 참조를 `send-notification.py`로 교체:
- `manage-schedule.sh` (3곳): `send-notification.py briefing` + `anomaly-monitor.py` 호출
- `healthcheck.py` ScriptsCheck: `send-notification.py`, `anomaly-monitor.py` 추가

### Cowork (Claude Desktop) 호환성

3번째 플랫폼으로 Cowork 지원 추가. 주요 대응:

| 제약 | 대응 |
|------|------|
| SessionStart 훅 없음 | CLAUDE.md 자동 로드 + `${SMART_BRIEFING_ROOT:-$(pwd)}` fallback |
| PreToolUse 훅 없음 | CLAUDE.md에 차트/PDF 규칙 명시 (자기 준수) |
| 슬래시 명령 없음 | 자연어 명령 (OpenClaw과 동일) |
| launchd/systemd 없음 | `manage-schedule.sh` 가드 + Cowork `/schedule` 안내 |
| HTTP 프록시 경유 | urllib이 `HTTP_PROXY` 환경변수 자동 인식 |
| macOS Homebrew 경로 | `utils.py` 플랫폼 가드 (`_IS_MACOS` 분기) |

`healthcheck.py`에 `ProxyCheck` 추가 (총 12개 항목).
`docs/cowork-setup.md` 설정 가이드 추가.
