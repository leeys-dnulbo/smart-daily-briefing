---
description: 브리핑 개인화 설정을 조회하거나 변경합니다. 프리셋 적용, 섹션 on/off, 임계값 변경을 지원합니다.
argument-hint: [show | preset {이름|list} | reset]
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
v2.1 미만이면 `python3 scripts/migrate-config.py --config config.json`을 실행하여 자동 마이그레이션합니다.

출력 형식의 상세 레이아웃은 `docs/template-customization-ui-spec.md`의 "1. 설정 조회" 섹션을 참조합니다.

```
현재 브리핑 설정:

| 항목 | 값 |
|------|-----|
| 버전 | {version} |
| 프리셋 | {preset} |
| 조회 기간 | {date_range} |
| 이상 탐지 임계값 | {anomaly_threshold}% |
| 최대 인사이트 | {max_insights}개 |
| 최대 액션 아이템 | {max_actions}개 |

내장 섹션:
[ON] 핵심 지표 오버뷰
[ON] 상위 페이지
...
[OFF] 캠페인 성과
...

커스텀 섹션:
{custom_sections가 있으면 각 섹션 표시}
{없으면: "(없음) 자연어로 추가: \"전환 퍼널 섹션 만들어줘\""}

알림: (상세: /smart-briefing:notification status)
{각 채널별: "Slack/Telegram/Discord 알림: 활성화됨/비활성화됨/미설정"}

내장 프리셋: default, behavior, traffic, campaign, content
커스텀 프리셋: {presets.custom 키 목록 또는 "(없음)"}
변경: /smart-briefing:customize preset {이름}
프리셋 목록: /smart-briefing:customize preset list
리셋: /smart-briefing:customize reset
```

### 인수가 "preset list"인 경우

내장 프리셋과 커스텀 프리셋 목록을 표시합니다.

```
사용 가능한 프리셋:

내장 프리셋:
  default   - 기본 (overview, top_pages, traffic_sources, daily_trend, device)
  behavior  - 사용자 행동패턴 (overview, user_behavior, top_pages, events, daily_trend)
  traffic   - 트래픽/유입 (overview, traffic_sources, landing_pages, daily_trend, device)
  campaign  - 캠페인 성과 (overview, campaigns, traffic_sources, landing_pages, daily_trend)
  content   - 콘텐츠 성과 (overview, top_pages, landing_pages, events, daily_trend)

커스텀 프리셋:
  {presets.custom 키 목록. 각각 sections_enabled 요약 표시}
  {없으면: "(없음) 현재 설정을 저장하려면 자연어로 요청하세요."}

적용: /smart-briefing:customize preset {이름}
```

### 인수가 "preset {이름}"인 경우

해당 프리셋을 적용합니다.

**내장 프리셋:**

| 프리셋 | 설명 | 활성 섹션 |
|--------|------|-----------|
| default | 기본 | overview, top_pages, traffic_sources, daily_trend, device |
| behavior | 사용자 행동패턴 | overview, user_behavior, top_pages, events, daily_trend |
| traffic | 트래픽/유입 | overview, traffic_sources, landing_pages, daily_trend, device |
| campaign | 캠페인 성과 | overview, campaigns, traffic_sources, landing_pages, daily_trend |
| content | 콘텐츠 성과 | overview, top_pages, landing_pages, events, daily_trend |

**프리셋 적용 절차:**
1. `config.json`을 읽습니다 (없으면 기본값 사용)
2. 내장 프리셋 이름이면 해당 정의대로 sections의 enabled 값을 변경
3. 내장에 없으면 `presets.custom.{이름}`을 확인:
   - `sections_enabled` → 내장 섹션 enabled 설정
   - `custom_sections_included` → 커스텀 섹션 enabled 설정 (삭제된 섹션 ID는 무시)
   - `overrides` → 파라미터 오버라이드 적용
4. 커스텀에도 없으면: "'{이름}' 프리셋을 찾을 수 없습니다." 에러 (스펙 6-4 참조)
5. preset 필드를 업데이트합니다
6. `config.json`을 저장합니다
7. 변경 결과를 보여줍니다

**참고**: 예약어(list, show, reset) 및 내장 프리셋명은 커스텀 프리셋 이름으로 사용 불가합니다. 이 규칙은 프리셋 저장 시 적용됩니다.

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

### 인수가 "notification"으로 시작하는 경우

> v2.0부터 알림 관련 기능은 `/smart-briefing:notification` 커맨드로 분리되었습니다.

안내 메시지를 출력한 뒤, 해당 기능을 실행합니다:
```
[안내] 알림 관련 기능이 /smart-briefing:notification 커맨드로 분리되었습니다.
다음부터: /smart-briefing:notification {서브커맨드}
```

그리고 요청된 동작을 그대로 실행합니다:
- `notification test` → `python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" test`
- `notification status` → `python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" status`
- `notification flush` → `python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" flush`
- `notification history` → `python3 "${SMART_BRIEFING_ROOT}/scripts/anomaly-monitor.py" history`
- `notification setup {채널}` → `/smart-briefing:notification setup {채널}` 안내
