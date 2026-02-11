# Agent Architecture - Smart Daily Briefing

## 전체 구조 개요

Smart Daily Briefing은 **Claude Code 플러그인**으로, 사용자의 GA4 데이터를 대화형으로 분석합니다.
플러그인 내부에는 크게 3가지 계층의 AI 구성요소가 존재합니다.

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 (User)                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Claude Code (Host)                      │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Skills     │  │   Commands   │  │    Agents     │  │
│  │  (자동실행)   │  │  (슬래시명령)  │  │  (서브에이전트) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                   │          │
│         └────────────────┼───────────────────┘          │
│                          │                              │
│                          ▼                              │
│              ┌──────────────────────┐                   │
│              │   GA4 MCP Server     │                   │
│              │  (google-analytics)  │                   │
│              └──────────┬───────────┘                   │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │   Google Analytics  │
               │     Data API        │
               └─────────────────────┘
```

---

## 구성요소별 역할

### 1. Skills (자동 트리거)

사용자의 자연어 입력에 자동으로 반응하는 스킬입니다.

| 스킬 | 파일 | 트리거 예시 | 역할 |
|------|------|-----------|------|
| **ga-analyst** | `skills/ga-analyst/SKILL.md` | "이번 주 세션 수 보여줘" | GA4 데이터 조회 및 분석 |
| **report-manager** | `skills/report-manager/SKILL.md` | "리포트로 저장해줘" | 리포트 저장/스케줄 관리 |

```
사용자: "모바일 이탈률이 어떻게 돼?"
         │
         ▼
   ┌─────────────┐     ┌──────────────┐     ┌──────────┐
   │ ga-analyst   │────▶│ GA4 MCP 조회  │────▶│ 결과 포맷  │
   │ (자동 트리거)  │     │ get_ga4_data │     │ 테이블 출력 │
   └─────────────┘     └──────────────┘     └──────────┘
```

### 2. Commands (슬래시 커맨드)

사용자가 명시적으로 호출하는 커맨드입니다.

| 커맨드 | 파일 | 용도 |
|--------|------|------|
| `/smart-briefing:setup` | `commands/setup.md` | 초기 설정 및 MCP 연결 확인 |
| `/smart-briefing:briefing` | `commands/briefing.md` | 일일 종합 브리핑 생성 |
| `/smart-briefing:reports` | `commands/reports.md` | 저장된 리포트 목록 조회 |
| `/smart-briefing:schedule` | `commands/schedule.md` | 스케줄 설정 및 관리 |

### 3. Agents (서브에이전트)

Claude Code가 내부적으로 활용하는 전문가 에이전트입니다. 개발/유지보수 시 사용됩니다.

| 에이전트 | 파일 | 모델 | 도구 | 역할 |
|---------|------|------|------|------|
| **planner** | `.claude/agents/planner.md` | inherit | Read, Grep, Glob | 기능 기획 및 구현 계획 |
| **code-writer** | `.claude/agents/code-writer.md` | haiku | Read, Write, Edit, Bash, Glob, Grep | 코드 작성 및 적용 |
| **code-reviewer** | `.claude/agents/code-reviewer.md` | inherit | Read, Grep, Glob | 품질 리뷰 (Read-only) |
| **ga4-data-expert** | `.claude/agents/ga4-data-expert.md` | inherit | Read, Grep, Glob | GA4 쿼리 설계 전문가 |
| **plugin-tester** | `.claude/agents/plugin-tester.md` | haiku | Read, Grep, Glob, Bash | E2E 동작 검증 |

---

## Agent 상세

### planner

```
역할: 기능 기획 및 구현 계획 수립
모델: inherit (호스트 모델과 동일)
권한: Read-only
```

**사용 시점:**
- 새 스킬 또는 커맨드 추가 시
- GA4 분석 기능 확장 시
- 플러그인 구조 리팩토링 시

**워크플로우:**
```
요구사항 분석 → 영향 범위 파악 → 작업 분해 → 리스크 식별
```

**출력물:**
- 요구사항 분석서
- 작업 분해 (Task Breakdown)
- 리스크 분석표
- GA4 데이터 요구사항

---

### code-writer

```
역할: 스킬/커맨드/설정 파일 작성 및 검증
모델: haiku (속도 최적화)
권한: Read + Write
```

**사용 시점:**
- 새 파일 생성 또는 기존 파일 수정 시
- planner의 계획을 실제 코드로 구현할 때

**워크플로우:**
```
프롬프트 파싱 → 코드 적용 → 포맷 검증 → 결과 보고
```

**체크리스트:**
- 한국어 사용자 대면 텍스트
- GA4 MCP 도구명 정확성
- 파일 저장 경로 규칙 준수
- CLAUDE.md 반영 여부

---

### code-reviewer

```
역할: 변경사항 품질 리뷰
모델: inherit (정확도 우선)
권한: Read-only (절대 수정 안 함)
```

**사용 시점:**
- code-writer가 파일 작성을 완료한 후
- PR 리뷰 시

**검수 항목:**

```
┌─────────────────────────────────────────┐
│            Review Criteria              │
├─────────────┬───────────────────────────┤
│ 플러그인 구조  │ 파일 위치, 프론트매터, 파일명    │
├─────────────┼───────────────────────────┤
│ GA4 연동     │ 도구명, 차원/메트릭, 날짜 포맷   │
├─────────────┼───────────────────────────┤
│ 한국어 품질   │ 자연스러운 표현, 용어 일관성      │
├─────────────┼───────────────────────────┤
│ 데이터 포맷   │ JSON 스키마, 숫자 포맷          │
├─────────────┼───────────────────────────┤
│ 일관성       │ 기존 패턴 준수, CLAUDE.md 등록   │
├─────────────┼───────────────────────────┤
│ 보안        │ 자격 증명 노출, 민감 데이터       │
└─────────────┴───────────────────────────┘
```

**결과:** `PASS` / `NEEDS_IMPROVEMENT` / `FAIL`

---

### ga4-data-expert

```
역할: GA4 데이터 모델 및 쿼리 설계 전문가
모델: inherit (분석 정확도 우선)
권한: Read-only
```

**사용 시점:**
- 새로운 GA4 분석 기능 설계 시
- 사용자 자연어를 GA4 쿼리로 매핑할 때
- 데이터 해석 가이드가 필요할 때

**핵심 매핑 테이블:**

| 사용자 표현 | Dimension | Metric |
|-----------|-----------|--------|
| 트래픽 현황 | `date` | `sessions`, `totalUsers`, `newUsers` |
| 인기 페이지 | `pagePath` | `screenPageViews`, `averageSessionDuration` |
| 유입 경로 | `sessionSource`, `sessionMedium` | `sessions`, `bounceRate` |
| 기기별 분석 | `deviceCategory` | `sessions`, `totalUsers`, `bounceRate` |
| 이벤트 분석 | `eventName` | `eventCount`, `eventValue` |
| 캠페인 성과 | `sessionCampaignName` | `sessions`, `conversions` |

**이상치 탐지 기준:**
- 전주 대비 **+20%** 이상 → 급증 (원인 분석 권장)
- 전주 대비 **-20%** 이상 → 급감 (즉시 확인)
- 이탈률 **+10%p** 이상 → 페이지 문제 확인

---

### plugin-tester

```
역할: 플러그인 End-to-End 동작 검증
모델: haiku (속도 최적화)
권한: Read + Bash (검증 명령 실행)
```

**사용 시점:**
- 변경사항 적용 후 배포 전
- 새 스킬/커맨드 추가 후

**검증 단계:**

```
1. 구조 검증        파일 존재 여부
       │
       ▼
2. 프론트매터 검증    YAML 유효성
       │
       ▼
3. 일관성 검증      CLAUDE.md ↔ 실제 파일
       │
       ▼
4. MCP 설정 검증    .mcp.json 구조
       │
       ▼
5. JSON 스키마 검증  리포트/브리핑 포맷
       │
       ▼
6. 한국어 검증      용어 일관성
       │
       ▼
    결과 보고       PASS / PARTIAL / FAIL
```

---

## Agent 간 협업 흐름

일반적인 기능 개발 시 에이전트들은 다음 순서로 협업합니다:

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ planner  │────▶│ code-writer │────▶│code-reviewer │────▶│plugin-tester │
│ 계획 수립  │     │  코드 작성    │     │  품질 리뷰     │     │  동작 검증     │
└──────────┘     └─────────────┘     └──────────────┘     └───────────────┘
      │                                      │
      │          ┌────────────────┐           │
      └─────────▶│ga4-data-expert│◀──────────┘
                 │ 쿼리 설계 자문   │
                 └────────────────┘
```

### 시나리오 예시: "시간대별 트래픽 분석 기능 추가"

| 단계 | 에이전트 | 수행 내용 |
|------|---------|----------|
| 1 | **planner** | 요구사항 분석, 영향 파일 파악, 작업 분해 |
| 2 | **ga4-data-expert** | `dateHour` 차원 + `sessions` 메트릭 매핑 설계 |
| 3 | **code-writer** | ga-analyst 스킬에 시간대 분석 로직 추가 |
| 4 | **code-reviewer** | 변경사항 리뷰 (GA4 도구명, 한국어, 일관성) |
| 5 | **plugin-tester** | 전체 플러그인 구조 및 동작 검증 |

---

## 프로젝트 디렉토리 구조

```
smart-daily-briefing/
│
├── .claude/
│   └── agents/                    ← 서브에이전트 정의
│       ├── planner.md
│       ├── code-writer.md
│       ├── code-reviewer.md
│       ├── ga4-data-expert.md
│       └── plugin-tester.md
│
├── .claude-plugin/                ← 플러그인 매니페스트
│   ├── plugin.json
│   └── marketplace.json
│
├── skills/                        ← 자동 트리거 스킬
│   ├── ga-analyst/
│   │   └── SKILL.md
│   └── report-manager/
│       └── SKILL.md
│
├── commands/                      ← 슬래시 커맨드
│   ├── setup.md
│   ├── briefing.md
│   ├── reports.md
│   └── schedule.md
│
├── reports/                       ← 저장된 리포트 (JSON)
├── briefings/                     ← 생성된 브리핑 (MD)
│
├── .mcp.json                      ← MCP 서버 설정 (gitignored)
├── .mcp.json.example              ← MCP 설정 템플릿
├── CLAUDE.md                      ← 플러그인 컨텍스트
├── README.md                      ← 사용 가이드
└── TODO.md                        ← 프로젝트 상태
```

---

## 모델 배정 전략

| 모델 | 에이전트 | 선택 이유 |
|------|---------|----------|
| **inherit** (Opus/Sonnet) | planner, code-reviewer, ga4-data-expert | 분석 정확도와 판단력이 중요 |
| **haiku** | code-writer, plugin-tester | 속도가 중요, 지시사항이 명확 |

---

## MCP 연동 구조

```
┌─────────────────────┐
│   .mcp.json         │
│                     │
│  ga4-analytics:     │
│    command: pipx    │
│    args: run        │
│      google-        │
│      analytics-mcp  │
│    env:             │
│      CREDENTIALS    │──────▶ Service Account JSON
│      PROPERTY_ID    │──────▶ GA4 Property ID
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  MCP 도구 목록        │     │  사용 가능한 조회      │
├─────────────────────┤     ├─────────────────────┤
│ search_schema       │     │ 차원/메트릭 검색       │
│ get_ga4_data        │     │ 데이터 조회           │
│ get_property_schema │     │ 전체 스키마           │
│ list_dimension_     │     │ 차원 카테고리          │
│   categories        │     │                     │
│ list_metric_        │     │ 메트릭 카테고리        │
│   categories        │     │                     │
│ get_dimensions_     │     │ 카테고리별 차원        │
│   by_category       │     │                     │
│ get_metrics_        │     │ 카테고리별 메트릭       │
│   by_category       │     │                     │
└─────────────────────┘     └─────────────────────┘
```
