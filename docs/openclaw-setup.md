# OpenClaw에서 Smart Daily Briefing 사용하기

Smart Daily Briefing 스킬을 OpenClaw 환경에서 사용하는 방법을 안내합니다.

## 사전 요구사항

- [OpenClaw](https://openclaw.ai/) 설치 및 실행
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

OpenClaw을 재시작한 후, 채팅에서 테스트합니다:

```
이번 주 세션 수 알려줘
```

GA4 데이터가 정상적으로 조회되면 설정 완료입니다.

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
| 스케줄링 | macOS launchd | OpenClaw cron (크로스 플랫폼) |
| 알림 | Slack 웹훅 | 멀티채널 (Telegram, Discord 등) |
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

## 보안 주의사항

1. **크레덴셜 관리**: GA4 서비스 계정 JSON 파일은 `chmod 600`으로 권한 설정
2. **환경 변수 사용**: `openclaw.json`에 민감한 값을 직접 넣지 말고 OS 환경 변수 사용 권장
3. **접근 제어**: OpenClaw 채널 설정 시 `allowedUsers`를 반드시 설정하여 허가된 사용자만 접근 가능하도록 제한
