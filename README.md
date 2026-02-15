# Smart Daily Briefing

GA4 데이터를 대화형으로 조회하고, 리포트를 저장하고, 일일 브리핑을 생성하는 AI 에이전트 플러그인입니다.
**Claude Code**와 **OpenClaw** 두 플랫폼에서 모두 사용할 수 있습니다.

## 사전 요구사항

- **공통**: Google Cloud 서비스 계정 JSON 파일, GA4 Property ID, `pipx`
- **Claude Code**: Claude Code 1.0.33+
- **OpenClaw**: OpenClaw 최신 버전

## 설치

### Claude Code에서 설치

```bash
# 마켓플레이스에서 설치
/plugin marketplace add leeys-dnulbo/smart-daily-briefing
/plugin install smart-briefing@smart-daily-briefing

# 또는 로컬에서 직접 실행
claude --plugin-dir ./smart-daily-briefing
```

GA4 MCP 서버는 플러그인에 포함되어 있어 자동으로 설치/실행됩니다.

#### MCP 서버 설정

```bash
cp .mcp.json.example .mcp.json
```

`.mcp.json`을 열어 실제 값을 입력하세요:

```json
{
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

설정 후 Claude Code를 재시작하면 바로 사용 가능합니다.

```
/smart-briefing:setup
```

### OpenClaw에서 설치

> 상세 가이드: [docs/openclaw-setup.md](docs/openclaw-setup.md)

1. `~/.openclaw/openclaw.json`에 스킬과 MCP 서버를 함께 설정합니다 (`openclaw.json.example` 참고):

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
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        "GA4_PROPERTY_ID": "your-property-id"
      }
    }
  }
}
```

2. OpenClaw 재시작 후 테스트:

```
이번 주 세션 수 보여줘
```

---

## 사용 방법

### 자연어로 데이터 조회

GA 관련 질문을 하면 자동으로 데이터를 조회하고 분석합니다:

```
"이번 주 세션 수 보여줘"
"모바일 이탈률이 어떻게 돼?"
"트래픽 소스별 성과 비교해줘"
"어제 캠페인 성과 요약해줘"
```

이 기능은 Claude Code와 OpenClaw 모두에서 동일하게 동작합니다.

### 커맨드 (Claude Code 전용)

| 커맨드 | 설명 |
|--------|------|
| `/smart-briefing:setup` | 초기 설정 안내 (MCP 연결 확인) |
| `/smart-briefing:briefing` | GA4 데이터를 종합 분석하여 일일 브리핑 생성 |
| `/smart-briefing:customize` | 브리핑 개인화 설정 조회/변경 |
| `/smart-briefing:reports` | 저장된 리포트 목록 조회 |
| `/smart-briefing:schedule` | 리포트 스케줄 조회/설정/실행 |
| `/smart-briefing:export` | 브리핑 PDF 내보내기 |

OpenClaw에서는 커맨드 대신 자연어로 동일한 기능을 사용합니다:
- "브리핑 생성해줘" → 일일 브리핑 생성
- "브리핑 설정 보여줘" → 개인화 설정 조회
- "리포트 목록 보여줘" → 저장된 리포트 확인
- "PDF로 만들어줘" → 브리핑 PDF 내보내기

### PDF 내보내기

마크다운 브리핑을 차트 이미지가 포함된 PDF로 변환합니다:

```
/smart-briefing:export latest        # 최신 브리핑을 PDF로
/smart-briefing:export 2026-02-15    # 날짜 지정
"이 브리핑 PDF로 만들어줘"            # 자연어
```

브리핑 생성 시 PDF도 자동으로 함께 생성됩니다 (기본값). `config.json`에서 `export.auto_pdf`를 `false`로 설정하면 비활성화할 수 있습니다.

사전 요구사항: `pip install weasyprint markdown`

### 리포트 저장 및 스케줄

데이터 조회 후 자연어로 리포트를 관리할 수 있습니다:

```
"이 분석을 리포트로 저장해줘"
"매일 아침 9시에 받고 싶어"
```

### 자동 브리핑 스케줄

#### Claude Code (macOS launchd)

```
/smart-briefing:schedule install 09:00   # 매일 09:00에 자동 브리핑
/smart-briefing:schedule status          # 상태 확인
/smart-briefing:schedule uninstall       # 해제
```

#### OpenClaw (내장 cron)

```bash
# 매일 아침 9시 자동 브리핑
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘. config.json 설정에 따라 활성 섹션의 데이터를 수집하고 분석해."

# 스케줄 확인/해제
openclaw cron list
openclaw cron remove "GA4-daily-briefing"
```

OpenClaw cron은 크로스 플랫폼(macOS/Linux/Windows)이며 자동 재시도(exponential backoff)를 지원합니다.

### Slack 알림

자동 브리핑 생성 후 Slack으로 요약을 받을 수 있습니다:

```
"Slack webhook 등록해줘"
```

또는 `config.json`에 직접 설정:

```json
{
  "notifications": {
    "slack": {
      "webhook_url": "https://hooks.slack.com/services/T.../B.../...",
      "enabled": true
    }
  }
}
```

Slack Incoming Webhook 생성:
1. [Slack API](https://api.slack.com/messaging/webhooks) 접속
2. Slack App 생성 → Incoming Webhooks 활성화
3. Webhook URL 복사 후 등록

### 브리핑 개인화

브리핑 내용을 자연어로 맞춤 설정할 수 있습니다:

```
"사용자 행동패턴 위주로 브리핑해줘"
"캠페인 성과 중심으로 바꿔줘"
"이벤트 섹션 추가해줘"
"이상 탐지 임계값 30%로 높여줘"
```

---

## 프로젝트 구조

```
smart-daily-briefing/
├── .claude-plugin/
│   ├── plugin.json            # 플러그인 매니페스트 (Claude Code)
│   └── marketplace.json       # 마켓플레이스 배포 설정
├── .claude/agents/            # 서브에이전트 정의 (Claude Code)
├── skills/
│   ├── ga-analyst/
│   │   └── SKILL.md           # GA 데이터 자동 분석
│   ├── report-manager/
│   │   └── SKILL.md           # 리포트 관리 + OpenClaw 브리핑
│   ├── briefing-customizer/
│   │   └── SKILL.md           # 브리핑 개인화 설정
│   └── schedule-helper/
│       └── SKILL.md           # OpenClaw cron 스케줄 관리
├── commands/                  # 슬래시 커맨드 (Claude Code 전용)
│   ├── setup.md
│   ├── briefing.md
│   ├── customize.md
│   ├── reports.md
│   ├── schedule.md
│   └── export.md
├── scripts/
│   ├── generate-charts.py     # 차트 이미지 생성 (matplotlib/SVG)
│   ├── generate-pdf.py        # 브리핑 PDF 내보내기 (weasyprint)
│   ├── manage-schedule.sh     # 자동 브리핑 스케줄 관리 (launchd)
│   └── send-slack.sh          # Slack 웹훅 알림 전송
├── hooks/
│   ├── hooks.json             # 훅 설정 (SessionStart, PreToolUse)
│   ├── inject-plugin-root.sh  # $SMART_BRIEFING_ROOT 환경변수 주입
│   └── validate-chart-code.py # matplotlib/weasyprint 직접 사용 차단
├── fonts/
│   ├── NanumGothic-Regular.ttf # 번들 한국어 폰트 (컨테이너 환경용)
│   └── OFL.txt                # SIL Open Font License
├── docs/
│   └── openclaw-setup.md      # OpenClaw 설치/설정 가이드
├── config.json.example        # 브리핑 개인화 설정 템플릿
├── .mcp.json.example          # MCP 서버 설정 템플릿 (Claude Code)
├── openclaw.json.example      # MCP 서버 설정 템플릿 (OpenClaw)
├── CLAUDE.md                  # 자동 로드 컨텍스트
├── reports/                   # 저장된 리포트 (.json)
└── briefings/                 # 생성된 브리핑 (.md, .pdf, charts/)
```

---

## 플랫폼별 기능 비교

| 기능 | Claude Code | OpenClaw |
|------|-------------|----------|
| 자연어 GA4 조회 | O | O |
| 일일 브리핑 생성 | O (슬래시 명령) | O (자연어) |
| 브리핑 개인화 | O | O |
| 리포트 저장/실행 | O | O |
| 차트 이미지 생성 | O | O (Python 필요) |
| PDF 내보내기 | O (weasyprint 필요) | O (weasyprint 필요) |
| 자동 스케줄링 | macOS launchd | OpenClaw cron (크로스 플랫폼) |
| Slack 알림 | O (웹훅) | O (웹훅 또는 네이티브 채널) |
| 멀티채널 알림 | - | Telegram, Discord 등 (향후) |
| 슬래시 커맨드 | O | - |

---

## GA4 연동 가이드

### Step 1: Google Cloud 프로젝트 설정

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 프로젝트 생성 (또는 기존 프로젝트 선택)
3. **API 및 서비스 > 라이브러리**에서 **Google Analytics Data API** 검색 후 **사용 설정**

### Step 2: 서비스 계정 생성

1. **API 및 서비스 > 사용자 인증 정보** 이동
2. **+ 사용자 인증 정보 만들기 > 서비스 계정** 클릭
3. 서비스 계정 이름 입력 (예: `ga-briefing-reader`)
4. 역할은 생략 가능 (GA 권한은 별도 설정)
5. 완료 후 생성된 서비스 계정 클릭
6. **키** 탭 > **키 추가 > 새 키 만들기 > JSON** 선택
7. 다운로드된 JSON 파일을 안전한 위치에 저장

### Step 3: GA4 속성에 서비스 계정 권한 부여

1. [Google Analytics](https://analytics.google.com) 접속
2. **관리(톱니바퀴)** > **속성 > 속성 액세스 관리** 이동
3. **+** 버튼 > **사용자 추가**
4. 서비스 계정 이메일 입력 (JSON 파일의 `client_email` 값)
5. 역할: **뷰어** (읽기 전용) 선택 후 추가

### Step 4: GA4 Property ID 확인

1. Google Analytics > **관리** > **속성 설정 > 속성 세부정보**
2. **속성 ID** (숫자) 복사

### Step 5: 플랫폼별 설정

**Claude Code:**
```bash
cp .mcp.json.example .mcp.json
# GOOGLE_APPLICATION_CREDENTIALS와 GA4_PROPERTY_ID 수정
```

**OpenClaw:**
```bash
# openclaw.json에 mcpServers 섹션 추가 (openclaw.json.example 참고)
```

---

## 차트 이미지 생성 (선택)

브리핑에 차트 이미지를 포함하려면 Python 3.9+가 필요합니다.

```bash
# matplotlib 설치 시 → PNG 차트 (고품질)
pip install matplotlib

# matplotlib 미설치 시 → SVG 차트 (순수 Python, 설치 불필요)
```

브리핑 생성 시 자동으로 차트 스크립트가 실행됩니다. Python이 없거나 스크립트 실행이 실패하면 Unicode 텍스트 차트로 대체됩니다.

한국어 폰트는 플러그인에 번들된 NanumGothic을 우선 사용하므로 컨테이너 환경에서도 별도 폰트 설치 없이 동작합니다.

---

## 마켓플레이스 배포

### Claude Code

GitHub에 push하면 다른 사용자가 설치할 수 있습니다:

```bash
claude plugin marketplace add leeys-dnulbo/smart-daily-briefing
claude plugin install smart-briefing@smart-daily-briefing
```

### 플러그인 업데이트

```bash
claude plugin marketplace update smart-daily-briefing
claude plugin install smart-briefing@smart-daily-briefing
```
