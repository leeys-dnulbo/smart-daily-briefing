---
description: AI 일일 브리핑을 생성합니다. config.json 설정에 따라 개인화된 GA4 브리핑을 제공합니다.
---

# 일일 브리핑 생성

GA4 데이터를 종합적으로 수집하고 분석하여 일일 브리핑을 생성하세요.

## 1단계: 설정 로드

`config.json` 파일을 읽으세요. 파일이 없으면 아래 기본 설정을 사용합니다.

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

`compare_previous: true`인 섹션은 추가로 이전 기간도 조회합니다:
- date_range가 "7daysAgo"이면 → 이전 기간: startDate "14daysAgo", endDate "8daysAgo"
- date_range가 "30daysAgo"이면 → 이전 기간: startDate "60daysAgo", endDate "31daysAgo"

## 3단계: 브리핑 작성

아래 형식으로 한국어 브리핑을 작성하세요. 활성화된 섹션만 포함합니다.

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

{각 활성 섹션에 대해 해당 섹션의 데이터를 테이블로 표시}

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

## 4단계: 저장

브리핑을 `briefings/{오늘날짜}.md` 파일로 저장하세요.
예: `briefings/2026-02-11.md`

저장 후 사용자에게 안내하세요:

```
브리핑이 briefings/{날짜}.md에 저장되었습니다.

현재 프리셋: {preset} ({활성 섹션 수}개 섹션)
설정 변경: /smart-briefing:customize 또는 자연어로 요청
매일 자동으로 브리핑을 받아보시겠어요?
```
