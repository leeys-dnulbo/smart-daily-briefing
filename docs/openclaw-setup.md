# OpenClaw에서 Smart Daily Briefing 사용하기

Smart Daily Briefing 스킬을 OpenClaw 환경에서 사용하는 방법을 안내합니다.

## 사전 요구사항

- [OpenClaw](https://openclaw.ai/) v0.8.0 이상 설치 및 실행
  - `openclaw --version`으로 현재 버전 확인
  - v0.8.0 미만이면 `skills.load.extraDirs` 및 `cron` 기능이 지원되지 않을 수 있습니다
- Google Cloud 서비스 계정 (GA4 Data API 접근 권한)
- GA4 Property ID
- `pipx` 설치 (`brew install pipx` 또는 `pip install pipx`)
- Python 3.9+ (차트 이미지 생성 시 선택, 없으면 텍스트 차트로 대체)

## 1단계: 스킬 등록 + MCP 서버 설정

`~/.openclaw/openclaw.json`에 스킬 디렉토리와 GA4 MCP 서버를 함께 설정합니다.

> 아래 두 섹션(`skills`와 `mcpServers`)은 **하나의 `openclaw.json` 파일**에 합쳐서 작성합니다.
> 전체 예시는 프로젝트 루트의 `openclaw.json.example`을 참고하세요.

### 방법 A: extraDirs로 등록 (권장)

```json
{
  "skills": {
    "load": {
      "extraDirs": ["/path/to/smart-daily-briefing/skills"]
    }
  },
  "mcpServers": {
    "ga4-analytics": {
      "command": "pipx",
      "args": ["run", "google-analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/your-service-account.json",
        "GA4_PROPERTY_ID": "your-property-id"
      }
    }
  }
}
```

### 방법 B: 심볼릭 링크 (스킬 등록만)

스킬 등록을 심볼릭 링크로 하는 경우, `mcpServers`는 `openclaw.json`에 별도로 추가해야 합니다:

```bash
ln -s /path/to/smart-daily-briefing/skills/ga-analyst ~/.openclaw/skills/ga-analyst
ln -s /path/to/smart-daily-briefing/skills/report-manager ~/.openclaw/skills/report-manager
ln -s /path/to/smart-daily-briefing/skills/briefing-customizer ~/.openclaw/skills/briefing-customizer
ln -s /path/to/smart-daily-briefing/skills/schedule-helper ~/.openclaw/skills/schedule-helper
```

> **보안 권장사항**: 크레덴셜은 `openclaw.json`에 직접 넣는 대신 OS 레벨 환경 변수를 사용하세요.
>
> ```bash
> # ~/.zshrc 또는 ~/.bashrc에 추가
> export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"
> export GA4_PROPERTY_ID="your-property-id"
> ```
>
> 그런 다음 `openclaw.json`에서는 환경 변수만 참조합니다:
> ```json
> {
>   "mcpServers": {
>     "ga4-analytics": {
>       "command": "pipx",
>       "args": ["run", "google-analytics-mcp"]
>     }
>   }
> }
> ```

### Google Cloud 서비스 계정 생성

서비스 계정이 없다면:

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. **IAM 및 관리자** > **서비스 계정** > **서비스 계정 만들기**
3. JSON 키 다운로드
4. **Google Analytics Data API** 활성화 (APIs & Services > Enable APIs)
5. GA4 속성에서 서비스 계정 이메일에 **뷰어** 권한 부여

## 2단계: 동작 확인

OpenClaw를 재시작한 후, 채팅에서 테스트합니다:

```
이번 주 세션 수 알려줘
```

GA4 데이터가 정상적으로 조회되면 설정 완료입니다.

## 3단계: 헬스 체크

설정이 올바르게 작동하는지 아래 명령으로 확인할 수 있습니다:

```bash
# OpenClaw 버전 확인
openclaw --version

# MCP 서버 연결 상태 확인
openclaw mcp status

# 등록된 스킬 목록 확인
openclaw skills list

# cron 스케줄 목록 확인
openclaw cron list

# GA4 MCP 서버 단독 테스트 (pipx로 직접 실행)
pipx run google-analytics-mcp --health-check
```

정상 동작 시 `ga4-analytics` MCP 서버가 `connected` 상태로 표시되어야 합니다.

## 사용 가능한 스킬

| 스킬 | 설명 | 트리거 예시 |
|------|------|-------------|
| ga-analyst | GA4 데이터 조회/분석 | "이번 주 트래픽", "이탈률 높은 페이지" |
| report-manager | 리포트 저장/실행/브리핑 생성 | "리포트로 저장해줘", "브리핑 생성해줘" |
| briefing-customizer | 브리핑 설정 변경 | "캠페인 위주로 바꿔", "이벤트 섹션 추가" |
| schedule-helper | OpenClaw cron 스케줄 관리 | "매일 브리핑 보내줘", "스케줄 설정해줘" |

## Claude Code와의 차이점

| 기능 | Claude Code | OpenClaw |
|------|-------------|----------|
| 슬래시 명령 (`/smart-briefing:*`) | 지원 | 자연어로 요청 |
| 스케줄링 | macOS launchd / Linux systemd | OpenClaw cron (크로스 플랫폼) |
| 알림 | Slack 웹훅 | 멀티채널 (Slack, Telegram, Discord 등) |
| 차트 생성 | 지원 | 지원 (Python 필요) |

## OpenClaw 스케줄링 (cron)

OpenClaw의 내장 cron을 사용하여 자동 브리핑을 설정할 수 있습니다:

```bash
# 매일 아침 9시 브리핑
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘. config.json 설정에 따라 활성 섹션의 데이터를 수집하고 분석해."

# 스케줄 확인
openclaw cron list

# 스케줄 삭제
openclaw cron remove "GA4-daily-briefing"
```

> **참고**: 브리핑 생성 시 마크다운(`briefings/YYYY-MM-DD.md`) 외에 구조화된 JSON sidecar 파일(`briefings/YYYY-MM-DD.json`)도 함께 저장됩니다. 이 파일은 브리핑 비교, 주간 요약 등 후속 기능에서 활용됩니다.

## 채널 알림 설정

스케줄 실행 결과를 메시징 채널로 자동 전송할 수 있습니다.

### Slack 웹훅 설정

1. [Slack API](https://api.slack.com/apps)에서 앱을 생성합니다
2. **Incoming Webhooks**를 활성화하고 Webhook URL을 복사합니다
3. 환경 변수로 등록합니다:

```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
export SLACK_WEBHOOK_URL="<your-slack-webhook-url>"
```

4. `openclaw.json`의 `channels.slack`에서 `enabled`를 `true`로 변경합니다
5. cron 설정 시 `--announce` 옵션을 추가합니다:

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘." \
  --announce --channel slack --to "webhook:${SLACK_WEBHOOK_URL}"
```

### Telegram 연동 (향후 지원 예정)

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘." \
  --announce --channel telegram --to "chat:${TELEGRAM_CHAT_ID}"
```

### Discord 연동 (향후 지원 예정)

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘." \
  --announce --channel discord --to "webhook:${DISCORD_WEBHOOK_URL}"
```

## 보안 주의사항

1. **크레덴셜 관리**: GA4 서비스 계정 JSON 파일은 `chmod 600`으로 권한 설정
2. **환경 변수 사용**: `openclaw.json`에 민감한 값을 직접 넣지 말고 OS 환경 변수 사용 권장
3. **접근 제어**: OpenClaw 채널 설정 시 `allowedUsers`를 반드시 설정하여 허가된 사용자만 접근 가능하도록 제한
4. **Webhook URL 보호**: Slack/Discord Webhook URL은 반드시 환경 변수로 관리하고, 코드 저장소에 커밋하지 마세요

## 트러블슈팅

### MCP 서버 연결 실패

**증상**: "GA4 MCP 서버가 연결되지 않았습니다" 메시지가 표시됨

**해결 방법**:

1. `pipx`가 설치되어 있는지 확인:
   ```bash
   which pipx
   # 없으면: brew install pipx && pipx ensurepath
   ```

2. `google-analytics-mcp` 패키지 실행 가능 여부 확인:
   ```bash
   pipx run google-analytics-mcp --version
   ```

3. 환경 변수가 올바르게 설정되었는지 확인:
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   echo $GA4_PROPERTY_ID
   ```

4. 서비스 계정 JSON 파일이 존재하고 읽기 가능한지 확인:
   ```bash
   ls -la "$GOOGLE_APPLICATION_CREDENTIALS"
   cat "$GOOGLE_APPLICATION_CREDENTIALS" | python3 -m json.tool > /dev/null
   ```

### 스킬이 인식되지 않음

**증상**: 자연어 요청 시 스킬이 트리거되지 않음

**해결 방법**:

1. `openclaw.json`의 `skills.load.extraDirs` 경로가 올바른지 확인:
   ```bash
   ls /path/to/smart-daily-briefing/skills/
   # ga-analyst, report-manager, briefing-customizer, schedule-helper 디렉토리가 보여야 함
   ```

2. 심볼릭 링크를 사용하는 경우 링크가 유효한지 확인:
   ```bash
   ls -la ~/.openclaw/skills/
   ```

3. OpenClaw를 재시작하여 스킬을 다시 로드:
   ```bash
   openclaw restart
   # 또는 OpenClaw 프로세스를 종료 후 재시작
   ```

### GA4 API 권한 오류 (403 Forbidden)

**증상**: "Permission denied" 또는 "403" 오류 발생

**해결 방법**:

1. Google Cloud Console에서 **Google Analytics Data API**가 활성화되었는지 확인
2. 서비스 계정 이메일이 GA4 속성에 **뷰어** 이상의 권한으로 추가되었는지 확인:
   - GA4 관리자 > 계정 액세스 관리 > 서비스 계정 이메일 추가
3. GA4 Property ID가 올바른지 확인 (GA4 관리자 > 속성 설정 > 속성 ID)

### cron 스케줄이 실행되지 않음

**증상**: 설정한 시간에 브리핑이 생성되지 않음

**해결 방법**:

1. cron 작업이 등록되었는지 확인:
   ```bash
   openclaw cron list
   ```

2. 타임존 설정이 올바른지 확인 (`--tz "Asia/Seoul"`)

3. OpenClaw 데몬이 실행 중인지 확인:
   ```bash
   openclaw status
   ```

4. cron 로그에서 오류 확인:
   ```bash
   openclaw cron logs "GA4-daily-briefing"
   ```

### Python/차트 관련 오류

**증상**: 차트 생성 실패 또는 한글이 깨짐

**해결 방법**:

1. Python 3.9+ 설치 확인:
   ```bash
   python3 --version
   ```

2. 필요한 패키지 설치:
   ```bash
   pip3 install matplotlib pandas
   ```

3. 차트 생성은 반드시 내장 스크립트를 사용 (한글 폰트 자동 감지 포함):
   ```bash
   python3 scripts/generate-charts.py \
     --input briefings/charts/2026-02-26/data.json \
     --output-dir briefings/charts/2026-02-26/ \
     --format auto
   ```
