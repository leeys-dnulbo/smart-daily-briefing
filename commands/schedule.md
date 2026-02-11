---
description: 리포트 스케줄을 조회하거나 관리합니다. 자동 브리핑 스케줄 설치/해제도 지원합니다.
argument-hint: [list | 리포트이름 | run 리포트이름 | install [HH:MM] | uninstall | status]
---

# 스케줄 관리

$ARGUMENTS

## 동작

인수에 따라 아래와 같이 동작하세요:

### 인수가 없거나 "list"인 경우

`reports/` 디렉토리의 모든 JSON 파일을 읽어서 스케줄이 설정된 리포트만 표시합니다.
추가로 자동 브리핑 스케줄 상태도 함께 표시합니다.

1. Bash 도구로 자동 브리핑 상태를 확인합니다:
   ```bash
   bash scripts/manage-schedule.sh status
   ```

2. 결과를 아래 형식으로 표시합니다:

```
## 자동 브리핑
{status 결과에 따라: "매일 HH:MM에 자동 실행 중" 또는 "미설정 (`/smart-briefing:schedule install` 로 설정)"}

## 리포트 스케줄

| 리포트 | 빈도 | 시간 | 요일 | 상태 |
|--------|------|------|------|------|
| {name} | {frequency} | {time} | {day_of_week 또는 "-"} | 활성/비활성 |

스케줄이 설정되지 않은 리포트: {N}개
```

스케줄이 하나도 없으면:
```
설정된 스케줄이 없습니다.
리포트를 먼저 저장한 뒤, 스케줄을 설정할 수 있습니다.
```

### 인수가 리포트 이름인 경우

해당 리포트의 스케줄을 설정하거나 변경합니다.

1. `reports/` 디렉토리에서 이름이 일치하는 리포트를 찾습니다
2. 사용자에게 빈도를 물어봅니다: 매일 / 매주 / 매월
3. 매주인 경우 요일을 물어봅니다
4. 시간을 물어봅니다 (기본값: 09:00)
5. 리포트 JSON의 schedule 필드를 업데이트합니다

### 인수가 "run {리포트이름}"인 경우

해당 리포트를 즉시 실행합니다.

1. `reports/` 디렉토리에서 이름이 일치하는 리포트를 찾습니다
2. query 정보를 기반으로 `get_ga4_data` MCP 도구를 호출합니다
3. 결과를 분석하여 인사이트와 함께 표시합니다

### 인수가 "install" 또는 "install HH:MM"인 경우

macOS launchd를 이용하여 매일 자동 브리핑 스케줄을 설치합니다.

**환경 감지:** 먼저 현재 환경이 macOS인지 확인합니다.
- macOS가 아닌 경우 (Cowork/Linux VM 등): launchd를 사용할 수 없습니다.
  사용자에게 Cowork shortcut 생성을 제안하세요:
  ```
  현재 환경에서는 launchd를 사용할 수 없습니다.
  Cowork shortcut으로 스케줄을 설정할까요?
  ```
  사용자가 동의하면 `/create-shortcut` 명령을 실행하여 매일 {HH:MM}에 `/smart-briefing:briefing`을 실행하는 shortcut을 생성해주세요.
  `/create-shortcut`이 사용 불가능한 환경이면 로컬 macOS 터미널에서 수동으로 설정하는 방법을 안내합니다:
  ```
  로컬 macOS 터미널에서 다음 명령을 실행하세요:
  bash {플러그인경로}/scripts/manage-schedule.sh install {HH:MM}
  ```

- macOS인 경우:
  1. 시간이 지정되지 않으면 사용자에게 물어봅니다 (기본값: 09:00)
  2. Bash 도구로 실행합니다:
     ```bash
     bash scripts/manage-schedule.sh install {HH:MM}
     ```
  3. 결과를 확인하고 안내합니다:
     ```
     자동 브리핑 스케줄이 설정되었습니다!
     - 시간: 매일 {HH:MM}
     - 브리핑 결과: briefings/{날짜}.md
     - 실행 로그: briefings/schedule.log
     - Slack 알림: {config.json에 webhook_url이 있으면 "활성화됨", 없으면 "미설정 (\"Slack webhook 등록해줘\"로 설정)"}

     변경: /smart-briefing:schedule install {다른시간}
     해제: /smart-briefing:schedule uninstall
     ```

### 인수가 "uninstall"인 경우

자동 브리핑 스케줄을 해제합니다.

1. Bash 도구로 실행합니다:
   ```bash
   bash scripts/manage-schedule.sh uninstall
   ```
2. 결과를 안내합니다:
   - "OK"이면: "자동 브리핑 스케줄이 해제되었습니다."
   - "NONE"이면: "설정된 스케줄이 없습니다."

### 인수가 "status"인 경우

현재 자동 브리핑 스케줄 상태를 확인합니다.

1. Bash 도구로 실행합니다:
   ```bash
   bash scripts/manage-schedule.sh status
   ```
2. 결과를 표시합니다:
   - "ACTIVE"이면: 매일 실행 시간, Slack 알림 상태, 마지막 실행 기록을 표시
   - "SLACK: 활성화됨" 또는 "SLACK: 미설정"도 함께 표시
   - "NONE"이면: "자동 브리핑이 설정되어 있지 않습니다. `/smart-briefing:schedule install` 로 설정할 수 있습니다."

### 리포트를 찾을 수 없는 경우

```
'{이름}' 리포트를 찾을 수 없습니다.
`/smart-briefing:reports` 로 저장된 리포트 목록을 확인해주세요.
```
