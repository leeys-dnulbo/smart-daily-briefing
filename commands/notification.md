---
description: 알림 채널을 관리합니다. 테스트, 상태 확인, 채널 설정, 실패 큐 재전송을 지원합니다.
argument-hint: "[test | status | flush | history | setup 채널]"
---

# 알림 관리

$ARGUMENTS

## 동작

### 인수가 없는 경우

현재 알림 상태를 요약합니다.

```bash
python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" status
```

출력 예시:
```
알림 채널 상태:
  [slack]    활성
  [telegram] 미설정
  [discord]  미설정

대기 중인 메시지: 없음

채널 설정: /smart-briefing:notification setup {채널}
테스트: /smart-briefing:notification test
```

### 인수가 "test"인 경우

모든 활성 채널에 테스트 메시지를 전송합니다.

```bash
python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" test
```

성공 시:
```
[slack] 테스트 메시지 전송 성공
[telegram] 테스트 메시지 전송 성공
```

채널 이름이 추가로 지정된 경우 (예: `test slack`):
해당 채널의 설정 여부를 확인한 후 해당 채널만 테스트합니다.

### 인수가 "status"인 경우

채널별 연결 상태와 큐 대기 메시지를 상세히 확인합니다.

```bash
python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" status
```

### 인수가 "flush"인 경우

전송 실패로 큐에 쌓인 메시지를 재전송합니다.

```bash
python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" flush
```

출력 예시:
```
플러시 완료: 2건 전송, 0건 실패
```

### 인수가 "history"인 경우

이상 탐지 알림의 발송/억제 이력을 표시합니다.

```bash
python3 "${SMART_BRIEFING_ROOT}/scripts/anomaly-monitor.py" history
```

### 인수가 "setup {채널}"인 경우

사용자에게 해당 채널의 설정을 안내하고 값을 받아 `config.json`에 저장합니다.

#### Slack 설정
1. Webhook URL을 입력받습니다
2. URL이 `https://hooks.slack.com/services/`로 시작하는지 검증합니다 (다른 `https://` URL은 경고 후 허용)
3. `config.json`의 `notifications.slack.webhook_url`에 저장합니다
4. `notifications.slack.enabled`를 `true`로 설정합니다
5. 테스트 메시지 전송: `python3 "${SMART_BRIEFING_ROOT}/scripts/send-notification.py" test`

#### Telegram 설정
1. Bot Token을 입력받습니다 (@BotFather에서 발급)
2. Chat ID를 입력받습니다 (봇에게 `/start` 전송 후 확인)
3. `config.json`의 `notifications.telegram` 섹션에 저장합니다
4. `notifications.telegram.enabled`를 `true`로 설정합니다
5. 테스트 메시지 전송

#### Discord 설정
1. Webhook URL을 입력받습니다 (서버 설정 → 연동 → 웹훅)
2. URL이 `https://discord.com/api/webhooks/`로 시작하는지 검증합니다
3. `config.json`의 `notifications.discord` 섹션에 저장합니다
4. `notifications.discord.enabled`를 `true`로 설정합니다
5. 테스트 메시지 전송

### 알림 비활성화

사용자가 특정 채널의 알림을 끄겠다고 하면:
- `config.json`의 `notifications.{채널}.enabled`를 `false`로 설정합니다

### 응답 형식

```
{채널} 알림이 설정되었습니다!
테스트 메시지를 해당 채널에서 확인해주세요.

현재 활성 채널: {활성 채널 목록}
```
