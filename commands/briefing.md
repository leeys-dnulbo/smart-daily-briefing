---
description: AI 브리핑을 생성합니다. weekly 주간 요약, compare 날짜 비교, list 히스토리가 가능합니다.
argument-hint: "[daily | weekly | compare | list]"
---

# 브리핑 생성

## 인수 처리

`$ARGUMENTS`를 확인하여 모드를 결정합니다:
- 인수 없음 또는 `daily`: **일일 브리핑** (아래 "일일 브리핑 생성" 섹션)
- `weekly`: **주간 요약 브리핑** (아래 "주간 요약 브리핑" 섹션). 직전 완결 주(월~일) 기준.
- `weekly YYYY-MM-DD`: 해당 날짜가 속한 주의 주간 요약. 날짜는 해당 주의 월요일로 정렬됨.
- `compare`: **브리핑 비교** (아래 "브리핑 비교" 섹션). 직전 2일(어제 vs 그제) 비교.
- `compare YYYY-MM-DD YYYY-MM-DD`: 지정된 두 날짜의 브리핑 비교.
- `list`: **브리핑 히스토리** (아래 "브리핑 히스토리" 섹션). 최근 14일 브리핑 목록.

---

# 일일 브리핑 생성

> **차트/PDF 생성 규칙**: 반드시 플러그인 내장 스크립트(`generate-charts.py`, `generate-pdf.py`)를 사용하세요.
> 직접 matplotlib/weasyprint 코드를 작성하면 **PreToolUse 훅에 의해 자동 차단**됩니다.
> `$SMART_BRIEFING_ROOT` 환경변수가 SessionStart 훅에 의해 자동 설정됩니다.
> ```
> CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"
> ```

GA4 데이터를 종합적으로 수집하고 분석하여 일일 브리핑을 생성하세요.

## 사전 확인: MCP 서버 연결

`get_ga4_data` MCP 도구가 사용 가능한지 먼저 확인하세요.
사용할 수 없다면 브리핑 생성을 시도하지 말고 아래 메시지를 표시하세요:

```
GA4 MCP 서버가 연결되지 않았습니다.
`/smart-briefing:setup` 으로 초기 설정을 진행해주세요.
```

## 1단계: 설정 로드

`config.json` 파일을 읽으세요.
- 파일이 없으면 아래 기본 설정을 사용합니다.
- 파일이 존재하지만 JSON 파싱에 실패하면: "config.json이 손상되었습니다. 기본 설정으로 진행합니다. 복구: `/smart-briefing:customize reset`" 메시지를 표시하고 기본 설정을 사용합니다.

### 기본 설정 (config.json이 없을 때)

```json
{
  "version": "1.0",
  "preset": "default",
  "briefing": {
    "sections": [
      { "id": "overview", "name": "핵심 지표 오버뷰", "enabled": true, "metrics": ["sessions", "totalUsers", "newUsers", "bounceRate", "averageSessionDuration", "screenPageViews", "engagementRate"], "dimensions": [], "compare_previous": true },
      { "id": "top_pages", "name": "상위 페이지", "enabled": true, "metrics": ["screenPageViews", "averageSessionDuration", "bounceRate"], "dimensions": ["pagePath"], "limit": 10 },
      { "id": "traffic_sources", "name": "트래픽 소스", "enabled": true, "metrics": ["sessions", "totalUsers", "bounceRate"], "dimensions": ["sessionSource", "sessionMedium"], "limit": 10 },
      { "id": "daily_trend", "name": "일별 트렌드", "enabled": true, "metrics": ["sessions", "totalUsers"], "dimensions": ["date"] },
      { "id": "device", "name": "디바이스별 분석", "enabled": true, "metrics": ["sessions", "bounceRate", "averageSessionDuration"], "dimensions": ["deviceCategory"] },
      { "id": "campaigns", "name": "캠페인 성과", "enabled": false, "metrics": ["sessions", "totalUsers", "bounceRate"], "dimensions": ["sessionCampaignName", "sessionSource"], "limit": 10 },
      { "id": "events", "name": "이벤트 분석", "enabled": false, "metrics": ["eventCount", "totalUsers"], "dimensions": ["eventName"], "limit": 10 },
      { "id": "landing_pages", "name": "랜딩 페이지", "enabled": false, "metrics": ["sessions", "bounceRate", "averageSessionDuration"], "dimensions": ["landingPage"], "limit": 10 },
      { "id": "user_behavior", "name": "사용자 행동패턴", "enabled": false, "metrics": ["engagementRate", "sessionsPerUser", "screenPageViewsPerSession", "averageSessionDuration", "eventCount"], "dimensions": [], "compare_previous": true }
    ],
    "date_range": "7daysAgo",
    "anomaly_threshold": 20,
    "max_insights": 5,
    "max_actions": 4
  }
}
```

## 2단계: 데이터 수집

config의 `briefing.sections` 배열에서 **`enabled: true`인 섹션만** 순서대로 조회합니다.

각 섹션에 대해 `get_ga4_data`를 호출하세요:

- **dimensions**: 섹션의 `dimensions` 값 (⚠️ 아래 "빈 dimensions 처리" 참조)
- **metrics**: 섹션의 `metrics` 값
- **date_range_start**: config의 `briefing.date_range` 값 (예: "7daysAgo")
- **date_range_end**: "yesterday"
- **limit**: 섹션에 `limit`이 있으면 해당 값

### 빈 dimensions 처리

`get_ga4_data`는 빈 dimensions 배열(`[]`)을 지원하지 않습니다.
`dimensions`가 `[]`인 섹션(overview, user_behavior 등)은 다음과 같이 처리하세요:

1. `dimensions=["date"]`로 대체하여 호출
2. 반환된 일별 행들의 메트릭을 집계하여 단일 객체로 변환:
   - **합산(SUM)**: sessions, totalUsers, newUsers, screenPageViews, eventCount 등 카운트 메트릭
   - **가중 평균**: bounceRate, engagementRate, averageSessionDuration, sessionsPerUser, screenPageViewsPerSession 등 비율/평균 메트릭 (sessions를 가중치로 사용)

예시: 일별 7행 → 집계:
```
sessions: sum(각 행의 sessions)
bounceRate: sum(각 행의 bounceRate × sessions) / sum(sessions)
```

### compare_previous 처리

`compare_previous: true`인 섹션은 추가로 이전 기간도 조회합니다.
일반 공식: date_range가 N일이면 → 이전 기간: startDate "(N*2)daysAgo", endDate "(N+1)daysAgo"

예시:
- date_range가 "7daysAgo"이면 → 이전 기간: startDate "14daysAgo", endDate "8daysAgo"
- date_range가 "30daysAgo"이면 → 이전 기간: startDate "60daysAgo", endDate "31daysAgo"
- date_range가 "14daysAgo"이면 → 이전 기간: startDate "28daysAgo", endDate "15daysAgo"

## 2.5단계: 차트 이미지 생성

수집된 데이터로 차트 이미지를 생성합니다. 이 단계는 선택적이며, 실패해도 브리핑 생성은 계속됩니다.

### 2.5.1 데이터 JSON 저장

활성 섹션의 수집 데이터를 `briefings/charts/{오늘날짜}/data.json`에 저장하세요.

**data 필드 타입 규칙:**
- 일반 섹션: `data`는 GA4 조회 결과 **행 배열** (`[{...}, {...}]`)
- `compare_previous: true` 섹션 (overview, user_behavior): `data`는 `{"current": {...}, "previous": {...}}` **객체**
- 모든 메트릭 값은 **숫자** 타입으로 저장 (문자열 금지)

```json
{
  "date": "2026-02-11",
  "date_range": "7daysAgo",
  "anomaly_threshold": 20,
  "sections": {
    "{섹션ID}": {
      "name": "섹션 표시명",
      "data": [{GA4 조회 결과 행들}]
    },
    "overview": {
      "name": "핵심 지표 오버뷰",
      "data": {
        "current": {"sessions": 7500, "totalUsers": 5200, "bounceRate": 0.42},
        "previous": {"sessions": 6680, "totalUsers": 4780, "bounceRate": 0.45}
      }
    },
    "user_behavior": {
      "name": "사용자 행동패턴",
      "data": {
        "current": {"engagementRate": 0.58, "sessionsPerUser": 1.44, "averageSessionDuration": 185.3},
        "previous": {"engagementRate": 0.55, "sessionsPerUser": 1.40, "averageSessionDuration": 152.0}
      }
    }
  }
}
```

### 2.5.2 차트 생성 스크립트 실행

Bash 도구로 차트 스크립트를 실행합니다:

```bash
# $SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정
CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"
[ -z "$SMART_BRIEFING_ROOT" ] && CHART_SCRIPT=$(find "$HOME/.claude" "$HOME/Library/Application Support/Claude" -name "generate-charts.py" -path "*smart-daily-briefing*" 2>/dev/null | head -1)
[ -z "$CHART_SCRIPT" ] && CHART_SCRIPT="scripts/generate-charts.py"
PYTHON=$(command -v /opt/homebrew/bin/python3.13 || command -v /opt/homebrew/bin/python3.12 || command -v /opt/homebrew/bin/python3.11 || command -v python3) && \
$PYTHON "$CHART_SCRIPT" \
  --input briefings/charts/{오늘날짜}/data.json \
  --output-dir briefings/charts/{오늘날짜}/ \
  --format auto
```

> **스크립트를 찾을 수 없는 경우**: 차트 생성을 건너뛰고 3단계로 진행하세요.
> 직접 matplotlib 코드를 작성하면 PreToolUse 훅에 의해 차단됩니다.

- matplotlib 설치 시 PNG, 미설치 시 SVG로 자동 생성됩니다.
- 스크립트 실행이 실패하면 (Python 미설치 등) 차트 없이 3단계로 진행합니다.

### 2.5.3 결과 확인

`briefings/charts/{오늘날짜}/manifest.json`을 읽어 생성된 차트 목록과 형식을 확인합니다.

## 3단계: 브리핑 작성

아래 형식으로 한국어 브리핑을 작성하세요. 활성화된 섹션만 포함합니다.
**테이블과 함께 시각화 차트를 반드시 포함합니다.** (시각화 규칙은 아래 참조)

```markdown
# 일일 GA 브리핑 - {오늘 날짜 YYYY-MM-DD}

> 프리셋: {config.preset} | 조회 기간: 최근 {date_range}

## 핵심 요약
{전체 상황을 2~3문장으로 요약}

## 주요 지표
{overview 섹션이 활성화된 경우}

| 지표 | 현재 | 전주 | 변화율 |
|------|------|------|--------|
| ... | ... | ... | +/-% |

{각 활성 섹션에 대해: 테이블 + 시각화 차트를 함께 표시}

## 이상 탐지
전주 대비 +{anomaly_threshold}% 또는 -{anomaly_threshold}% 이상 변화한 지표를 나열.
변화가 없으면 "이상 탐지된 항목 없음"이라고 표시.

## 인사이트
{max_insights}개의 데이터 기반 인사이트.
- 각 인사이트 앞에 심각도 표시: [info] / [warning] / [critical]
- 구체적 수치를 포함

## 액션 아이템
{max_actions}개의 구체적 실행 방안.
- 각 항목에 우선순위 표시: [높음] / [중간] / [낮음]
```

### 시각화 규칙

터미널과 마크다운 파일 모두에서 보이도록 **Unicode 블록 문자**를 사용합니다.
블록 문자: `░` (빈칸), `█` (채움), `▏▎▍▌▋▊▉` (세밀 조절)

#### 1. 일별 트렌드 (daily_trend 섹션)

가로 막대 차트로 일별 추이를 표시합니다. 최대값 기준 바 길이를 정규화합니다 (최대 20칸).

```
일별 세션 트렌드:
02/05  ████████████████░░░░  982
02/06  ██████████████████░░ 1,102
02/07  ████████████████████ 1,234  ← 최대
02/08  ██████████░░░░░░░░░░   623
02/09  ████████████████░░░░   987
02/10  ███████████████████░ 1,180
02/11  █████████████████░░░ 1,054
```

#### 2. 트래픽 소스 / 캠페인 (traffic_sources, campaigns 섹션)

가로 막대 + 비율을 함께 표시합니다.

```
트래픽 소스별 세션:
google/organic   ████████████████████  45.2%  (1,842)
direct/(none)    ████████████░░░░░░░░  28.1%  (1,145)
naver/organic    ██████░░░░░░░░░░░░░░  14.3%    (583)
instagram/social ███░░░░░░░░░░░░░░░░░   7.8%    (318)
기타             ██░░░░░░░░░░░░░░░░░░   4.6%    (188)
```

#### 3. 디바이스 분포 (device 섹션)

한 줄 스택 바로 비율을 직관적으로 표시합니다.

```
디바이스 분포:
[████████████████░░░░░░░░░░░░░░] mobile 54% | desktop 32% | tablet 14%
 ← mobile ──────→← desktop ──→←tablet→
```

또는 가로 막대:
```
mobile   ████████████████████  54.2%  (2,210)
desktop  ████████████░░░░░░░░  32.1%  (1,308)
tablet   █████░░░░░░░░░░░░░░░  13.7%    (558)
```

#### 4. 상위 페이지 (top_pages, landing_pages 섹션)

가로 막대로 페이지뷰 규모를 표시합니다. 경로가 길면 앞 30자로 자릅니다.

```
상위 페이지 (페이지뷰):
/                          ████████████████████  3,421
/products/list             ██████████████░░░░░░  2,387
/blog/2026-new-feature     █████████░░░░░░░░░░░  1,542
/about                     ██████░░░░░░░░░░░░░░    987
/contact                   ███░░░░░░░░░░░░░░░░░    456
```

#### 5. 주요 지표 변화율 (overview 섹션)

변화율이 있는 overview에서는 방향 표시와 함께 시각적으로 보여줍니다.

```
전주 대비 변화:
세션               +12.3%  ▲ ████████████
사용자              +8.7%  ▲ █████████
신규 사용자          +5.2%  ▲ █████
페이지뷰           +15.1%  ▲ ███████████████
이탈률              -3.2%  ▼ ███          ← 개선
평균 세션 시간      +22.4%  ▲ ██████████████████████  ⚠️ 이상치
```

변화율 바 길이: |변화율|을 기준으로 1% = 1칸 (최대 20칸).
양수는 `▲`, 음수는 `▼`. anomaly_threshold 초과 시 `⚠️` 표시.

#### 시각화 일반 규칙

- **바 최대 길이**: 20칸 (좁은 터미널 대응)
- **정규화**: 각 차트 내 최대값을 20칸으로, 나머지는 비례 계산
- **숫자 포맷**: 천 단위 콤마 (1,234)
- **정렬**: 값 기준 내림차순
- **항목 수**: 섹션의 `limit` 값을 따름 (기본 상위 10개)
- **생략**: 항목이 limit보다 많으면 "기타"로 합산

## 4단계: 저장

브리핑은 **터미널 출력**과 **파일 저장** 두 가지 형태로 제공됩니다.

### 터미널 출력

Unicode 블록 차트가 포함된 브리핑을 터미널에 그대로 표시합니다 (위의 시각화 규칙 적용).

### JSON sidecar 저장

브리핑의 핵심 지표를 구조화된 JSON으로 `briefings/{오늘날짜}.json`에 저장합니다.
이 파일은 향후 브리핑 비교, 주간 요약 등의 기능에서 활용됩니다.

```json
{
  "schema_version": "1.11",
  "date": "YYYY-MM-DD",
  "preset": "default",
  "date_range": "7daysAgo",
  "anomaly_threshold": 20,
  "metrics": {
    "sessions": { "current": 7500, "previous": 6680, "change_pct": 12.3 },
    "totalUsers": { "current": 5200, "previous": 4780, "change_pct": 8.8 },
    "newUsers": { "current": 2100, "previous": 1950, "change_pct": 7.7 },
    "bounceRate": { "current": 0.42, "previous": 0.45, "change_pct": -6.7 },
    "averageSessionDuration": { "current": 185.3, "previous": 152.0, "change_pct": 21.9 },
    "screenPageViews": { "current": 12400, "previous": 10800, "change_pct": 14.8 },
    "engagementRate": { "current": 0.58, "previous": 0.55, "change_pct": 5.5 }
  },
  "anomalies": [
    { "metric": "averageSessionDuration", "change_pct": 21.9, "severity": "warning" }
  ],
  "insights": [
    { "severity": "info", "text": "모바일 트래픽이 54%로 전주 대비 3.2%p 증가" }
  ],
  "comparable_keys": ["sessions", "totalUsers", "newUsers", "bounceRate", "averageSessionDuration", "screenPageViews", "engagementRate"],
  "top_sources": [
    { "source": "google/organic", "sessions": 1842, "share_pct": 45.2 }
  ],
  "top_pages": [
    { "path": "/", "pageviews": 3421 }
  ]
}
```

**sidecar JSON 생성 규칙:**
- `schema_version`: 반드시 `"1.11"` 문자열.
- `metrics`: overview 섹션의 현재/이전 기간 값과 변화율. 이전 기간이 없으면 `previous`와 `change_pct`를 `null`로.
- `anomalies`: `anomaly_threshold` 이상 변화한 지표 목록. severity는 threshold 기준: threshold 이상 ~ threshold × 1.5 미만 = "warning", threshold × 1.5 이상 = "critical".
- `insights`: 브리핑에서 도출한 인사이트 목록 (최대 `max_insights`개).
- `comparable_keys`: metrics의 키 목록 (정렬됨). 향후 비교 기능에서 사용.
- `top_sources`: traffic_sources 섹션 상위 5개. 섹션이 비활성이면 빈 배열.
- `top_pages`: top_pages 섹션 상위 5개. 섹션이 비활성이면 빈 배열.

### 파일 저장

브리핑을 `briefings/{오늘날짜}.md` 파일로 저장합니다.

**차트 이미지가 생성된 경우:**
- `manifest.json`의 `format` 필드 (png 또는 svg)를 확인합니다.
- 저장용 마크다운에서 각 Unicode 차트 블록을 이미지 링크로 교체합니다:
  ```markdown
  ![일별 트렌드](charts/{오늘날짜}/daily_trend.{format})
  ```
- `{format}`은 manifest의 `format` 값을 사용합니다 (png 또는 svg).
- 이미지 경로는 `briefings/` 기준 상대경로입니다.

**차트 이미지가 생성되지 않은 경우:**
- Unicode 블록 차트가 포함된 마크다운을 그대로 저장합니다.

### PDF 자동 생성

브리핑 저장 후 항상 PDF도 함께 생성합니다. (config.json의 `export.auto_pdf`가 `false`이면 건너뜁니다.)
**파일명 규칙**: 반드시 `briefings/YYYY-MM-DD.pdf` 형식. 한국어나 부가 텍스트를 파일명에 포함하지 않습니다.

Bash 도구로 실행:
```bash
# $SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정
PDF_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-pdf.py"
[ -z "$SMART_BRIEFING_ROOT" ] && PDF_SCRIPT=$(find "$HOME/.claude" "$HOME/Library/Application Support/Claude" -name "generate-pdf.py" -path "*smart-daily-briefing*" 2>/dev/null | head -1)
[ -z "$PDF_SCRIPT" ] && PDF_SCRIPT="scripts/generate-pdf.py"
PYTHON=$(command -v /opt/homebrew/bin/python3.13 || command -v /opt/homebrew/bin/python3.12 || command -v /opt/homebrew/bin/python3.11 || command -v python3) && \
$PYTHON "$PDF_SCRIPT" \
  --input briefings/{오늘날짜}.md \
  --output briefings/{오늘날짜}.pdf \
  --charts-dir briefings/charts/{오늘날짜}/
```

- 성공 시: "PDF도 함께 저장되었습니다: briefings/{날짜}.pdf"
- 실패 시 (weasyprint 미설치 등): 무시하고 계속 진행합니다 (에러 로그만 표시)

`export.auto_pdf`가 명시적으로 `false`이면 이 단계를 건너뜁니다. 설정이 없거나 `true`이면 실행합니다.

### 저장 후 안내

```
브리핑이 briefings/{날짜}.md에 저장되었습니다.
{차트 이미지가 있으면: "차트 이미지 {N}개가 briefings/charts/{날짜}/에 저장되었습니다. (형식: PNG/SVG)"}

현재 프리셋: {preset} ({활성 섹션 수}개 섹션)
설정 변경: /smart-briefing:customize 또는 자연어로 요청
매일 자동으로 브리핑을 받아보시겠어요?
```

---

# 주간 요약 브리핑

> `$ARGUMENTS`가 `weekly` 또는 `weekly YYYY-MM-DD`일 때 이 섹션을 실행합니다.

주간 요약은 일일 sidecar JSON 파일 7일분을 집계하여 한 주의 전체 트렌드를 단일 문서로 제공합니다.

## 사전 확인

일일 브리핑과 동일하게 `get_ga4_data` MCP 도구 사용 가능 여부를 먼저 확인하세요.

## W1단계: 대상 주 결정

- `weekly` (인수 없음): 직전 완결 주의 월~일. 예: 오늘이 2026-02-26(목)이면 → 2026-02-16(월) ~ 2026-02-22(일)
- `weekly YYYY-MM-DD`: 해당 날짜가 속한 주. 날짜가 월요일이 아니면 해당 주의 월요일로 정렬.

대상 주의 시작일(월요일)과 종료일(일요일)을 결정하세요.

## W2단계: sidecar 수집 및 집계

### 2-1. sidecar 파일 수집

`briefings/YYYY-MM-DD.json` 파일 7개(월~일)를 탐색합니다.

각 sidecar 파일을 읽을 때:
1. JSON 파싱
2. `schema_version` 필드가 없으면 정규화 필요 (v1.10.0 이전 파일)
3. `comparable_keys` 필드가 없으면 metrics 키 목록으로 자동 생성

### 2-2. sidecar 부족 시 fallback

- 7일 중 **4일 이상** sidecar가 존재하면: sidecar 기반 집계 진행 (누락일은 건너뜀)
- 7일 중 **3일 이하**이면: GA4 직접 조회로 fallback
  - 이번주: `date_range_start`=월요일, `date_range_end`=일요일
  - 전주: 이전 7일 동일 범위
  - 일일 브리핑 2단계와 동일한 방식으로 데이터 수집

### 2-3. 메트릭 집계 규칙

sidecar의 `metrics` 값을 집계합니다:

- **합산(SUM) 메트릭**: sessions, totalUsers, newUsers, screenPageViews, eventCount 등
  - 7일간 `current` 값의 합계
- **비율/평균(RATE) 메트릭**: bounceRate, engagementRate, averageSessionDuration, sessionsPerUser 등
  - 7일간 `sessions` 가중 평균: `Σ(metric × sessions) / Σ(sessions)`

전주 비교: 동일한 방식으로 이전 7일(또는 sidecar의 `previous` 값)을 집계하여 전주 대비 변화율을 계산합니다.

## W3단계: 주간 차트 생성

차트 데이터를 `briefings/charts/weekly-{시작일}/data.json`에 저장합니다.

```json
{
  "date": "{시작일}",
  "date_range": "weekly",
  "anomaly_threshold": 20,
  "sections": {
    "weekly_trend": {
      "name": "주간 일별 추이",
      "data": [
        {"date": "2026-02-16", "sessions": 1200, "totalUsers": 800},
        {"date": "2026-02-17", "sessions": 1350, "totalUsers": 920}
      ]
    },
    "weekly_comparison": {
      "name": "전주 대비 변화",
      "data": {
        "current": {"sessions": 8500, "bounceRate": 0.38},
        "previous": {"sessions": 7800, "bounceRate": 0.42}
      }
    },
    "traffic_sources": {
      "name": "주간 트래픽 소스",
      "data": [{"source": "google/organic", "sessions": 3800}]
    },
    "top_pages": {
      "name": "주간 상위 페이지",
      "data": [{"pagePath": "/", "screenPageViews": 12500}]
    }
  }
}
```

차트 생성 스크립트 실행:
```bash
CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"
[ -z "$SMART_BRIEFING_ROOT" ] && CHART_SCRIPT=$(find "$HOME/.claude" "$HOME/Library/Application Support/Claude" -name "generate-charts.py" -path "*smart-daily-briefing*" 2>/dev/null | head -1)
[ -z "$CHART_SCRIPT" ] && CHART_SCRIPT="scripts/generate-charts.py"
PYTHON=$(command -v /opt/homebrew/bin/python3.13 || command -v /opt/homebrew/bin/python3.12 || command -v /opt/homebrew/bin/python3.11 || command -v python3) && \
$PYTHON "$CHART_SCRIPT" \
  --input briefings/charts/weekly-{시작일}/data.json \
  --output-dir briefings/charts/weekly-{시작일}/ \
  --format auto
```

## W4단계: 주간 브리핑 작성

```markdown
# 주간 GA 브리핑 - {시작일} ~ {종료일}

> 프리셋: {preset} | 기간: {시작일(월)} ~ {종료일(일)} | 데이터 소스: sidecar {N}일 / GA4 fallback

## 주간 핵심 요약
{7일간 전체 트렌드를 3~4문장으로 요약. 전주 대비 주요 변화 포인트.}

## 주간 지표 추이
| 지표 | 월 | 화 | 수 | 목 | 금 | 토 | 일 | 주간 합계/평균 | 전주 대비 |
|------|---|---|---|---|---|---|---|-------------|----------|
| 세션 | 1,200 | 1,350 | ... | ... | ... | ... | ... | 8,500 | +9.0% |
| 이탈률 | 40% | 38% | ... | ... | ... | ... | ... | 38.5% | -3.5%p |

{차트 이미지가 있으면: ![주간 일별 추이](charts/weekly-{시작일}/weekly_trend.{format})}

## 전주 대비 변화
{overview 변화율 차트 + 테이블}

{차트 이미지가 있으면: ![전주 대비 변화](charts/weekly-{시작일}/weekly_comparison.{format})}

## 주간 이상 탐지 요약
{7일간 anomalies를 종합:
- 반복 발생한 이상 탐지 (예: "3일 연속 이탈률 이상")
- 최대 변화폭 기록
- 패턴 분석}

## 주간 인사이트
{7일간 insights를 종합하여 중복 제거 후 핵심 5개}

## 다음 주 주요 관찰 포인트
{데이터 기반 다음 주 주의사항 3~4개}
```

## W5단계: 저장

- 마크다운: `briefings/weekly-{시작일}.md`
- JSON sidecar: `briefings/weekly-{시작일}.json`
  - 일일 sidecar와 동일한 스키마 (`schema_version: "1.11"`)
  - `date`에 시작일, `date_range`에 `"weekly"`
  - `metrics`에 주간 집계 값
- PDF: `briefings/weekly-{시작일}.pdf` (auto_pdf 설정에 따름)

### 저장 후 안내

```
주간 브리핑이 briefings/weekly-{시작일}.md에 저장되었습니다.
기간: {시작일} ~ {종료일} (sidecar {N}일 사용{fallback이면: ", GA4 fallback 사용"})

매주 자동으로 주간 요약을 받아보시겠어요?
→ /smart-briefing:schedule install-weekly [HH:MM] [요일]
```

---

# 브리핑 비교

> `$ARGUMENTS`가 `compare` 또는 `compare YYYY-MM-DD YYYY-MM-DD`일 때 이 섹션을 실행합니다.

두 날짜의 sidecar JSON을 비교하여 지표 변화를 분석합니다.

## C1단계: 비교 대상 결정

- `compare` (인수 없음): 어제 vs 그제 (가장 최근 2일)
- `compare YYYY-MM-DD YYYY-MM-DD`: 지정된 두 날짜 비교. 첫 번째가 "이전", 두 번째가 "이후".

## C2단계: sidecar 로드

두 날짜의 `briefings/YYYY-MM-DD.json` sidecar 파일을 로드합니다.

파일이 없는 경우:
```
{날짜} sidecar 파일을 찾을 수 없습니다: briefings/{날짜}.json
먼저 해당 날짜의 브리핑을 생성해주세요: /smart-briefing:briefing daily
```

## C3단계: 지표 비교 분석

두 sidecar의 `comparable_keys`를 합집합으로 비교 대상을 결정합니다.
각 메트릭의 `current` 값을 비교하여 변화율을 계산합니다:

```
변화율 = ((이후 값 - 이전 값) / 이전 값) × 100
```

이전 값이 0이면 변화율을 "N/A"로 표시합니다.

### 비교 항목
- **주요 지표**: metrics의 모든 comparable_keys
- **트래픽 소스**: top_sources 변화 (있는 경우)
- **상위 페이지**: top_pages 변화 (있는 경우)
- **이상 탐지**: 두 날짜의 anomalies 비교

## C4단계: 비교 결과 출력

```markdown
# 브리핑 비교 - {이전 날짜} vs {이후 날짜}

## 주요 지표 변화

| 지표 | {이전 날짜} | {이후 날짜} | 변화율 |
|------|-----------|-----------|--------|
| 세션 | 6,680 | 7,500 | +12.3% ▲ |
| 사용자 | 4,780 | 5,200 | +8.8% ▲ |
| 이탈률 | 45.0% | 42.0% | -6.7% ▼ (개선) |
| ... | ... | ... | ... |

변화율 시각화:
세션               +12.3%  ▲ ████████████
사용자              +8.8%  ▲ █████████
이탈률              -6.7%  ▼ ███████        ← 개선
평균 세션 시간      +21.9%  ▲ ██████████████████████  ⚠️

## 트래픽 소스 변화
{두 날짜 모두 top_sources가 있으면 비교 테이블}

## 이상 탐지 비교
- {이전 날짜}: {N}건 — {메트릭 목록}
- {이후 날짜}: {M}건 — {메트릭 목록}
- 새로 발생: {새 이상 탐지 메트릭}
- 해소됨: {해소된 메트릭}

## 비교 요약
{2~3문장으로 주요 변화 포인트 요약}
```

비교 결과는 터미널에만 출력하고 파일로 저장하지 않습니다.

---

# 브리핑 히스토리

> `$ARGUMENTS`가 `list`일 때 이 섹션을 실행합니다.

최근 14일간 생성된 브리핑 파일을 조회하여 목록으로 표시합니다.

## L1단계: 파일 탐색

`briefings/` 디렉토리에서 최근 14일간의 파일을 탐색합니다:

- `briefings/YYYY-MM-DD.md` — 일일 브리핑
- `briefings/YYYY-MM-DD.json` — sidecar 데이터
- `briefings/YYYY-MM-DD.pdf` — PDF 파일
- `briefings/weekly-YYYY-MM-DD.md` — 주간 브리핑

## L2단계: 목록 출력

```markdown
# 브리핑 히스토리 (최근 14일)

| 날짜 | 타입 | 파일 | sidecar | PDF |
|------|------|------|---------|-----|
| 2026-02-26 | daily | briefings/2026-02-26.md | O | O |
| 2026-02-25 | daily | briefings/2026-02-25.md | O | - |
| 2026-02-24 | weekly | briefings/weekly-2026-02-17.md | O | O |
| 2026-02-23 | daily | briefings/2026-02-23.md | O | O |
| ... | ... | ... | ... | ... |

총 {N}개 브리핑 (일일 {D}개, 주간 {W}개)
sidecar 보유율: {sidecar 있는 일일 수}/{일일 총 수} ({비율}%)
```

파일이 없는 경우:
```
최근 14일간 생성된 브리핑이 없습니다.
브리핑을 생성하려면: /smart-briefing:briefing
```
