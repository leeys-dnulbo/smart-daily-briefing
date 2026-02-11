# Smart Daily Briefing

Claude Code 플러그인으로 GA4 데이터를 대화형으로 조회하고, 리포트를 저장하고, 일일 브리핑을 생성합니다.

## 사전 요구사항

- Claude Code 1.0.33+
- Google Cloud 서비스 계정 JSON 파일
- GA4 Property ID

## 설치

### 1. 플러그인 설치

```bash
# 마켓플레이스에서 설치하는 경우
/plugin marketplace add leeys-dnulbo/smart-daily-briefing
/plugin install smart-briefing@smart-daily-briefing

# 또는 로컬에서 직접 실행
claude --plugin-dir ./smart-daily-briefing
```

GA4 MCP 서버는 플러그인에 포함되어 있어 자동으로 설치/실행됩니다.

### 2. MCP 서버 설정

플러그인의 GA4 연동은 `.mcp.json` 파일로 설정합니다.

```bash
# 템플릿에서 복사
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
설정 상태를 확인하려면:

```
/smart-briefing:setup
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

### 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/smart-briefing:setup` | 초기 설정 안내 (MCP 연결 확인) |
| `/smart-briefing:briefing` | GA4 데이터를 종합 분석하여 일일 브리핑 생성 |
| `/smart-briefing:customize` | 브리핑 개인화 설정 조회/변경 |
| `/smart-briefing:reports` | 저장된 리포트 목록 조회 |
| `/smart-briefing:schedule` | 리포트 스케줄 조회/설정/실행 |

### 리포트 저장 및 스케줄

데이터 조회 후 자연어로 리포트를 관리할 수 있습니다:

```
"이 분석을 리포트로 저장해줘"
"매일 아침 9시에 받고 싶어"
"/smart-briefing:schedule run 모바일분석"
```

### 브리핑 개인화

브리핑 내용을 자연어로 맞춤 설정할 수 있습니다:

```
"사용자 행동패턴 위주로 브리핑해줘"
"캠페인 성과 중심으로 바꿔줘"
"이벤트 섹션 추가해줘"
"이상 탐지 임계값 30%로 높여줘"
"/smart-briefing:customize preset behavior"
```

---

## 프로젝트 구조

```
smart-daily-briefing/
├── .claude-plugin/
│   ├── plugin.json            # 플러그인 매니페스트
│   └── marketplace.json       # 마켓플레이스 배포 설정
├── .claude/agents/            # 서브에이전트 정의
├── skills/
│   ├── ga-analyst/
│   │   └── SKILL.md           # GA 데이터 자동 분석 (자동 트리거)
│   ├── report-manager/
│   │   └── SKILL.md           # 리포트 관리 (자동 트리거)
│   └── briefing-customizer/
│       └── SKILL.md           # 브리핑 개인화 설정 (자동 트리거)
├── commands/
│   ├── setup.md               # /smart-briefing:setup
│   ├── briefing.md            # /smart-briefing:briefing
│   ├── customize.md           # /smart-briefing:customize
│   ├── reports.md             # /smart-briefing:reports
│   └── schedule.md            # /smart-briefing:schedule
├── scripts/
│   └── generate-charts.py     # 차트 이미지 생성 (matplotlib/SVG)
├── config.json.example        # 브리핑 개인화 설정 템플릿
├── .mcp.json.example          # MCP 서버 설정 템플릿
├── CLAUDE.md                  # 자동 로드 컨텍스트
├── reports/                   # 저장된 리포트 (.json)
└── briefings/                 # 생성된 브리핑 (.md, charts/)
```

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

### Step 5: .mcp.json 설정

```bash
cp .mcp.json.example .mcp.json
```

`.mcp.json`의 두 값을 수정하세요:
- `GOOGLE_APPLICATION_CREDENTIALS`: 다운로드한 서비스 계정 JSON 파일의 **절대 경로**
- `GA4_PROPERTY_ID`: 복사한 속성 ID (숫자)

---

## 차트 이미지 생성 (선택)

브리핑에 차트 이미지를 포함하려면 Python 3.6+가 필요합니다.

```bash
# matplotlib 설치 시 → PNG 차트 (고품질)
pip install matplotlib

# matplotlib 미설치 시 → SVG 차트 (순수 Python, 설치 불필요)
```

브리핑 생성 시 자동으로 차트 스크립트가 실행됩니다. Python이 없거나 스크립트 실행이 실패하면 Unicode 텍스트 차트로 대체됩니다.

---

## 마켓플레이스 배포

GitHub에 push하면 다른 사용자가 설치할 수 있습니다:

```
/plugin marketplace add leeys-dnulbo/smart-daily-briefing
/plugin install smart-briefing@smart-daily-briefing
```
