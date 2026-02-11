---
description: 브리핑 개인화 설정을 조회하거나 변경합니다. 프리셋 적용, 섹션 on/off, 임계값 변경 등을 지원합니다.
argument-hint: [show | preset 이름 | reset]
---

# 브리핑 개인화 설정

$ARGUMENTS

## 동작

### config.json 오류 처리

`config.json`이 존재하지만 JSON 파싱에 실패하면:
```
config.json이 손상되었습니다. 기본 설정으로 표시합니다.
복구하려면: /smart-briefing:customize reset
```

### 인수가 없거나 "show"인 경우

`config.json`을 읽어 현재 설정을 표시합니다. 파일이 없으면 기본 설정을 보여줍니다.

```
현재 브리핑 설정:

| 항목 | 값 |
|------|-----|
| 프리셋 | {preset} |
| 조회 기간 | {date_range} |
| 이상 탐지 임계값 | {anomaly_threshold}% |
| 최대 인사이트 | {max_insights}개 |
| 최대 액션 아이템 | {max_actions}개 |

섹션:
✅ 핵심 지표 오버뷰
✅ 상위 페이지
...
❌ 캠페인 성과
...

알림:
{notifications.slack.webhook_url이 있으면: "Slack 알림: 활성화됨" 또는 "비활성화됨"}
{없으면: "Slack 알림: 미설정 (\"Slack webhook 등록해줘\"로 설정)"}

사용 가능한 프리셋: default, behavior, traffic, campaign, content
변경: /smart-briefing:customize preset {이름}
리셋: /smart-briefing:customize reset
```

### 인수가 "preset {이름}"인 경우

해당 프리셋을 적용합니다.

사용 가능한 프리셋:

| 프리셋 | 설명 | 활성 섹션 |
|--------|------|-----------|
| default | 기본 | overview, top_pages, traffic_sources, daily_trend, device |
| behavior | 사용자 행동패턴 | overview, user_behavior, top_pages, events, daily_trend |
| traffic | 트래픽/유입 | overview, traffic_sources, landing_pages, daily_trend, device |
| campaign | 캠페인 성과 | overview, campaigns, traffic_sources, landing_pages, daily_trend |
| content | 콘텐츠 성과 | overview, top_pages, landing_pages, events, daily_trend |

프리셋을 적용하려면:
1. `config.json`을 읽습니다 (없으면 기본값 사용)
2. 해당 프리셋에 맞게 sections의 enabled 값을 변경합니다
3. preset 필드를 업데이트합니다
4. `config.json`을 저장합니다
5. 변경 결과를 보여줍니다

### 인수가 "reset"인 경우

`config.json`을 삭제하여 기본 설정으로 되돌립니다.
삭제 전에 사용자에게 확인을 받습니다.

```
현재 설정을 삭제하고 기본값으로 되돌릴까요? (yes/no)
```

확인 후:
```
브리핑 설정을 기본값으로 되돌렸습니다.
config.json이 삭제되었습니다. 기본 프리셋(default)으로 동작합니다.
```
