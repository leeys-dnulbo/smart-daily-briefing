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

Cowork에서 프로젝트를 열면 `CLAUDE.md`가 자동으로 로드되어 에이전트 컨텍스트가 설정됩니다.
바로 자연어로 기능을 사용할 수 있습니다:

```
"이번 주 세션 수 보여줘"
"브리핑 생성해줘"
```

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
| 에이전트 컨텍스트 | CLAUDE.md 자동 로드 | SKILL.md 자동 로드 | CLAUDE.md 자동 로드 |
| 환경변수 주입 | SessionStart 훅 | 해당 없음 | pwd 기반 fallback |
| 코드 검증 훅 | PreToolUse 자동 | 해당 없음 | CLAUDE.md 규칙 준수 |
| 스케줄링 | launchd/systemd | openclaw cron | create_scheduled_task (앱 실행 중) |
| PDF 생성 | 지원 | 지원 | 제한적 |
| 알림 채널 | 멀티채널 | 멀티채널 | 제한적 |
| 상태 지속성 | 영구 | 영구 | 세션 단위 |

## 자동 스케줄

`/smart-briefing:schedule install` 명령을 실행하면, 에이전트가 Cowork 네이티브 `create_scheduled_task` 도구를 호출하여 자동 스케줄을 생성합니다.

### 설정 방법

에이전트가 자동으로 처리합니다:
```
/smart-briefing:schedule install 09:00
```

또는 수동으로 사이드바 "Scheduled" > "+ New task"에서 직접 생성:
- 프롬프트: "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘. config.json 설정에 따라 활성 섹션의 데이터를 수집하고 분석해."
- 주기: Daily, Weekly, Weekdays 등

### 제한사항

- 컴퓨터가 깨어있고 Claude Desktop 앱이 열려있을 때만 실행됩니다
- 놓친 실행은 앱 재시작 시 자동으로 실행됩니다
- `manage-schedule.sh`(launchd/systemd)는 Cowork 컨테이너에서 사용할 수 없습니다

## 기타 제한사항

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

- 프로젝트에 번들된 NanumGothic 폰트가 자동 감지됩니다 (`fonts/` 디렉토리)
- 반드시 `generate-charts.py` 스크립트를 통해 차트를 생성하세요 (자동 처리)

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
