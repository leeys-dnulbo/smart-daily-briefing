---
description: AI 일일 브리핑을 생성합니다. GA4 데이터를 종합 분석하여 핵심 인사이트와 액션 아이템을 제공합니다.
---

# 일일 브리핑 생성

GA4 데이터를 종합적으로 수집하고 분석하여 일일 브리핑을 생성하세요.

## 수집할 데이터

MCP 도구 `get_ga4_data`를 사용하여 아래 데이터를 모두 조회하세요:

1. **핵심 지표 오버뷰** (최근 7일)
   - metrics: sessions, totalUsers, newUsers, bounceRate, averageSessionDuration, screenPageViews, engagementRate, conversions
   - dimensions: 없음

2. **전주 동일 지표** (8~14일 전)
   - 위와 동일한 metrics, startDate: "14daysAgo", endDate: "8daysAgo"

3. **상위 페이지** (Top 10)
   - dimensions: pagePath
   - metrics: screenPageViews, averageSessionDuration, bounceRate

4. **트래픽 소스** (Top 10)
   - dimensions: sessionSource, sessionMedium
   - metrics: sessions, totalUsers

5. **일별 트렌드** (최근 7일)
   - dimensions: date
   - metrics: sessions, totalUsers

6. **디바이스별 분석**
   - dimensions: deviceCategory
   - metrics: sessions, bounceRate, averageSessionDuration

## 브리핑 형식

아래 형식으로 한국어 브리핑을 작성하세요:

```markdown
# 일일 GA 브리핑 - {오늘 날짜 YYYY-MM-DD}

## 핵심 요약
{전체 상황을 2~3문장으로 요약}

## 주요 지표

| 지표 | 현재 (7일) | 전주 (7일) | 변화율 |
|------|-----------|-----------|--------|
| 세션 | {값} | {값} | {+/-}% |
| 사용자 | {값} | {값} | {+/-}% |
| 신규 사용자 | {값} | {값} | {+/-}% |
| 이탈률 | {값}% | {값}% | {+/-}%p |
| 평균 체류시간 | {값}초 | {값}초 | {+/-}% |
| 페이지뷰 | {값} | {값} | {+/-}% |
| 참여율 | {값}% | {값}% | {+/-}%p |

## 인사이트

{3~5개의 데이터 기반 인사이트}
- 각 인사이트 앞에 심각도 표시: [info] / [warning] / [critical]
- 구체적 수치를 포함

## 액션 아이템

{2~4개의 구체적 실행 방안}
- 각 항목에 우선순위 표시: [높음] / [중간] / [낮음]

## 이상 탐지

전주 대비 +20% 또는 -20% 이상 변화한 지표를 나열하세요.
변화가 없으면 "이상 탐지된 항목 없음"이라고 표시하세요.

## 상위 페이지 (Top 5)

| 페이지 | 페이지뷰 | 체류시간 | 이탈률 |
|--------|---------|---------|--------|

## 트래픽 소스 (Top 5)

| 소스/매체 | 세션 | 사용자 |
|-----------|------|--------|
```

## 저장

브리핑을 `briefings/{오늘날짜}.md` 파일로 저장하세요.
예: `briefings/2026-02-10.md`

저장 후 사용자에게 안내하세요:
"브리핑이 `briefings/{날짜}.md`에 저장되었습니다. 매일 자동으로 브리핑을 받아보시겠어요?"
