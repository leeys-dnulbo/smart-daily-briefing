# Cowork (Claude Desktop)에서 Smart Daily Briefing 사용하기

Cowork(Claude Desktop) 환경에서 Smart Daily Briefing을 사용하는 방법을 안내합니다.

## 사전 요구사항

- Claude Desktop (Cowork 기능 포함) 설치
- Google Cloud 서비스 계정 (GA4 Data API 접근 권한)
- GA4 Property ID

## 1단계: MCP 서버 설정 (호스트 측)

MCP 서버는 **호스트 Claude Desktop 앱**에서 관리됩니다. 컨테이너 내부가 아닌 호스트 측에서 설정합니다.

Claude Desktop 설정 > MCP Servers에 `ga4-analytics`를 추가하세요:

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

> **참고**: 서비스 계정 JSON 파일은 호스트 파일시스템의 경로를 사용합니다.

서비스 계정이 없다면 [Google Cloud Console](https://console.cloud.google.com/)에서 생성하세요:
1. IAM 및 관리자 > 서비스 계정 > 서비스 계정 만들기
2. JSON 키 다운로드
3. Google Analytics Data API 활성화
4. GA4 속성에서 서비스 계정 이메일에 뷰어 권한 부여

## 2단계: 프로젝트 열기

Cowork에서 `smart-daily-briefing` 프로젝트 디렉토리를 엽니다.

## 3단계: 세션 시작

첫 메시지로 에이전트를 초기화합니다:

```
COWORK.md 읽어줘
```

또는:

```
Smart Daily Briefing 시작해줘
```

에이전트가 프로젝트 상태를 확인하고 사용 가능한 기능을 안내합니다.

## 사용 방법

자연어로 모든 기능을 사용합니다 (OpenClaw과 동일):

| 요청 예시 | 기능 |
|-----------|------|
| "브리핑 생성해줘" | 일일 브리핑 |
| "주간 브리핑 생성해줘" | 주간 브리핑 |
| "이번 주 세션 수 보여줘" | 데이터 조회 |
| "이 분석을 리포트로 저장해줘" | 리포트 저장 |
| "저장된 리포트 목록 보여줘" | 리포트 목록 |
| "캠페인 위주로 브리핑해줘" | 브리핑 개인화 |
| "브리핑 설정 보여줘" | 설정 확인 |
| "이 브리핑 PDF로 만들어줘" | PDF 내보내기 |
| "어제랑 그제 비교해줘" | 브리핑 비교 |
| "최근 브리핑 목록 보여줘" | 히스토리 |
| "환경 상태 점검해줘" | 헬스체크 |

## Claude Code / OpenClaw과의 차이점

| 기능 | Claude Code | OpenClaw | Cowork |
|------|:-----------:|:--------:|:------:|
| 입력 방식 | 슬래시 명령 + 자연어 | 자연어 | 자연어 |
| 에이전트 컨텍스트 | CLAUDE.md 자동 로드 | SKILL.md 자동 로드 | COWORK.md 수동 로드 |
| 환경변수 주입 | SessionStart 훅 | 해당 없음 | 수동 (pwd 기반) |
| 코드 검증 훅 | PreToolUse 자동 | 해당 없음 | 자기 준수 |
| 스케줄링 | launchd/systemd | openclaw cron | 미지원 |
| PDF 생성 | 지원 | 지원 | 제한적 |
| 알림 채널 | 멀티채널 | 멀티채널 | 제한적 |
| 상태 지속성 | 영구 | 영구 | 세션 단위 |

## 제한사항

### 자동 스케줄

Cowork 컨테이너는 ephemeral(임시)이므로 영구 스케줄을 설치할 수 없습니다.
매 세션에서 수동으로 "브리핑 생성해줘"를 요청하세요.

정기 브리핑이 필요하면:
- **Claude Code**: `manage-schedule.sh install 09:00`
- **OpenClaw**: `openclaw cron add ...`

### PDF 생성

weasyprint이 컨테이너에 미설치일 수 있습니다. 필요하면:

```bash
pip install weasyprint markdown
```

ARM64 Linux에서는 추가 시스템 라이브러리가 필요할 수 있습니다.
마크다운 브리핑은 항상 정상 생성됩니다.

### 세션 상태

대화 컨텍스트는 세션 종료 시 사라집니다.
브리핑/리포트 파일은 프로젝트 디렉토리에 저장되므로 파일 자체는 유지됩니다.

## 트러블슈팅

### GA4 MCP 서버 미연결

- Claude Desktop 설정에서 MCP 서버 등록 여부 확인
- 호스트 측 서비스 계정 파일 경로 확인
- Claude Desktop 재시작 후 재시도

### 한글 깨짐 (차트)

- 프로젝트에 포함된 NanumGothic 폰트가 자동 감지됩니다 (`fonts/` 디렉토리)
- `generate-charts.py` 스크립트를 통해 차트를 생성하면 자동 처리됩니다

### 네트워크 오류

Cowork 컨테이너는 프록시를 통해 네트워크에 접근합니다.
`HTTP_PROXY`/`HTTPS_PROXY` 환경변수가 설정되어 있는지 확인하세요:

```bash
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

환경 진단으로 상태를 점검할 수 있습니다:

```bash
python3 scripts/healthcheck.py
```
