---
description: AI 일일 브리핑을 생성합니다. config.json 설정에 따라 개인화된 GA4 브리핑을 제공합니다.
---

# 일일 브리핑 생성

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

- **dimensions**: 섹션의 `dimensions` 값
- **metrics**: 섹션의 `metrics` 값
- **date_range_start**: config의 `briefing.date_range` 값 (예: "7daysAgo")
- **date_range_end**: "yesterday"
- **limit**: 섹션에 `limit`이 있으면 해당 값

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
        "current": {메트릭별 현재 값},
        "previous": {메트릭별 이전 기간 값}
      }
    }
  }
}
```

### 2.5.2 차트 생성 스크립트 실행

Bash 도구로 다음 명령을 실행하세요:

```bash
python3 scripts/generate-charts.py \
  --input briefings/charts/{오늘날짜}/data.json \
  --output-dir briefings/charts/{오늘날짜}/ \
  --format auto
```

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

변화율 바 길이: |변화율|을 기준으로 1% = 1칸 (최대 25칸).
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

### 파일 저장

브리핑을 `briefings/{오늘날짜}.md` 파일로 저장합니다.

**차트 이미지가 생성된 경우:**
- 저장용 마크다운에서 각 Unicode 차트 블록을 이미지 링크로 교체합니다:
  ```markdown
  ![일별 트렌드](charts/{오늘날짜}/daily_trend.png)
  ```
- 이미지 경로는 `briefings/` 기준 상대경로입니다.

**차트 이미지가 생성되지 않은 경우:**
- Unicode 블록 차트가 포함된 마크다운을 그대로 저장합니다.

### 저장 후 안내

```
브리핑이 briefings/{날짜}.md에 저장되었습니다.
{차트 이미지가 있으면: "차트 이미지 {N}개가 briefings/charts/{날짜}/에 저장되었습니다. (형식: PNG/SVG)"}

현재 프리셋: {preset} ({활성 섹션 수}개 섹션)
설정 변경: /smart-briefing:customize 또는 자연어로 요청
매일 자동으로 브리핑을 받아보시겠어요?
```
