---
name: schedule-helper
description: 자동 브리핑/리포트 스케줄을 관리합니다. OpenClaw 환경에서는 cron 설정을, Claude Code 환경에서는 /smart-briefing:schedule 커맨드를 안내합니다. 예시: "매일 브리핑 받고 싶어", "스케줄 걸어줘", "자동으로 보내줘", "cron 설정"
metadata: {"openclaw":{"emoji":"⏰"}}
---

# OpenClaw 스케줄 관리 에이전트

OpenClaw 환경에서 GA4 브리핑과 리포트의 자동 실행 스케줄을 관리합니다.

## 트리거 구분

이 스킬은 **OpenClaw 환경에서 스케줄 관련 요청**이 있을 때 활성화됩니다.
Claude Code 환경에서는 `/smart-briefing:schedule` 커맨드를 안내합니다.

- "매일 브리핑 보내줘" → 이 스킬 (스케줄 설정)
- "브리핑 생성해줘" → report-manager (즉시 실행)
- "스케줄 상태 보여줘" → 이 스킬 (상태 조회)
- "cron 설정해줘" → 이 스킬 (스케줄 설정)

## 일일 브리핑 스케줄

### 설정

사용자가 자동 브리핑을 원하면, 시간과 빈도를 확인한 후 아래 명령을 안내합니다:

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "{분} {시} * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘. config.json 설정에 따라 활성 섹션의 데이터를 수집하고 분석해."
```

예시:
- "매일 아침 9시" → `--cron "0 9 * * *"`
- "매일 오후 6시" → `--cron "0 18 * * *"`
- "매주 월요일 9시" → `--cron "0 9 * * 1"`

### 조회

```bash
openclaw cron list
```

### 해제

```bash
openclaw cron remove "GA4-daily-briefing"
```

## 리포트별 스케줄

저장된 리포트에 개별 스케줄을 설정할 수 있습니다.

### 설정

1. `reports/` 디렉토리에서 해당 리포트 JSON을 확인합니다
2. 사용자에게 빈도(매일/매주)와 시간을 확인합니다
3. 아래 명령을 안내합니다:

```bash
openclaw cron add --name "GA4-report-{리포트파일명}" \
  --cron "{분} {시} * * {요일}" --tz "Asia/Seoul" \
  --session isolated \
  --message "reports/{리포트파일명}.json 리포트를 실행해줘. query 정보를 읽고 get_ga4_data로 데이터를 조회한 뒤 결과를 분석해서 보여줘."
```

> cron job 이름에는 리포트 파일명(kebab-case)을 사용합니다. 예: "모바일분석" → `GA4-report-mobile-analysis`

4. 리포트 JSON의 `schedule` 필드도 업데이트합니다

### 해제

```bash
openclaw cron remove "GA4-report-{리포트파일명}"
```

## 채널 전송 연동 (향후 지원 예정)

> **주의**: 현재 OpenClaw API 키 직렬화 보안 이슈(#11202)로 인해 이 기능은 권장하지 않습니다.
> 해당 이슈가 해결된 후 안전하게 사용할 수 있습니다. 아래는 향후 지원 예정 형식입니다.

OpenClaw 채널이 설정된 경우, 스케줄 실행 결과를 메시징 채널로 전송할 수 있습니다.
아래 중 사용하는 채널에 맞는 하나를 선택하세요:

```bash
# Telegram으로 전송
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘." \
  --announce --channel telegram --to "chat:{chat_id}"
```

```bash
# Slack으로 전송
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘." \
  --announce --channel slack --to "channel:{channel_id}"
```

> **보안 참고**: 채널 전송을 설정하기 전에 OpenClaw의 채널 토큰 보안 설정을 확인하세요.
> `openclaw.json`의 채널 토큰이 LLM 프롬프트에 노출될 수 있으므로, OS 환경 변수 사용을 권장합니다.

## 응답 형식

### 스케줄 설정 완료 시

```
스케줄이 설정되었습니다!

| 항목 | 값 |
|------|-----|
| 이름 | {cron job 이름} |
| 실행 주기 | {매일/매주 {요일}} {HH:MM} KST |
| 채널 전송 | {설정됨/미설정} |

확인: openclaw cron list
해제: openclaw cron remove "{이름}"
```

### 상태 조회 시

사용자에게 `openclaw cron list` 실행을 안내하고, 결과를 해석하여 보여줍니다.
