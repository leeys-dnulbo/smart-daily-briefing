---
description: Smart Briefing 초기 설정을 안내합니다. GA4 MCP 서버 연결 상태를 확인하고, 필요 시 사용자로부터 정보를 입력받아 .mcp.json을 생성합니다.
---

# Smart Briefing 초기 설정

사용자의 GA4 연동 상태를 점검하고, 필요한 설정을 대화형으로 진행하세요.

## 1단계: MCP 서버 연결 확인

`ga4-analytics` 관련 MCP 도구(예: `get_ga4_data`, `search_schema`)가 사용 가능한지 확인하세요.

### MCP 도구가 있는 경우 → 2단계로 이동

### MCP 도구가 없는 경우 → .mcp.json 자동 생성

사용자에게 두 가지 정보를 질문하세요:

**질문 1: Google Cloud 서비스 계정 JSON 파일 경로**

```
GA4 데이터에 접근하려면 Google Cloud 서비스 계정 JSON 파일이 필요합니다.
파일의 절대 경로를 알려주세요. (예: /Users/이름/Downloads/service-account.json)
```

- 사용자가 경로를 입력하면, 해당 파일이 실제로 존재하는지 확인하세요.
- 파일이 없으면 다시 입력을 요청하세요.
- 서비스 계정이 아직 없으면 아래 생성 가이드를 안내하세요.

**질문 2: GA4 Property ID**

```
GA4 속성 ID를 알려주세요. (숫자, 예: 123456789)

확인 방법: Google Analytics → 관리 → 속성 설정 → 속성 세부정보 → 속성 ID
```

**두 값을 모두 받으면 .mcp.json을 자동 생성하세요:**

```json
{
  "mcpServers": {
    "ga4-analytics": {
      "command": "pipx",
      "args": ["run", "google-analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "{사용자가 입력한 JSON 파일 경로}",
        "GA4_PROPERTY_ID": "{사용자가 입력한 Property ID}"
      }
    }
  }
}
```

생성 후 안내:

```
.mcp.json 파일을 생성했습니다.
MCP 서버를 연결하려면 Claude Code를 재시작해주세요.
재시작 후 /smart-briefing:setup 을 다시 실행하면 연결 테스트를 진행합니다.
```

### 서비스 계정이 없는 경우 (생성 가이드)

```
GA4 연동을 위해 Google Cloud 서비스 계정이 필요합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[서비스 계정 생성]
1. https://console.cloud.google.com 접속
2. 프로젝트 생성 (또는 기존 프로젝트 선택)
3. "API 및 서비스 > 라이브러리"에서 "Google Analytics Data API" 검색 → 사용 설정
4. "API 및 서비스 > 사용자 인증 정보" → "+ 사용자 인증 정보 만들기" → "서비스 계정"
5. 이름 입력 (예: ga-briefing-reader) → 완료
6. 생성된 서비스 계정 클릭 → "키" 탭 → "키 추가" → "새 키 만들기" → JSON
7. 다운로드된 JSON 파일을 안전한 위치에 저장

[GA4 권한 부여]
1. https://analytics.google.com 접속
2. 관리(톱니바퀴) → 속성 → 속성 액세스 관리
3. "+" → "사용자 추가"
4. JSON 파일 안의 client_email 값 입력
5. 역할: "뷰어" 선택 → 추가

[Property ID 확인]
1. Google Analytics → 관리 → 속성 설정 → 속성 세부정보
2. "속성 ID" (숫자) 복사

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

완료 후 다시 알려주세요. 자동으로 설정을 진행하겠습니다.
```

## 2단계: GA4 데이터 연결 테스트

`get_ga4_data` 도구로 최근 7일 세션 수를 조회합니다.

### 연결 성공 시

```
설정 완료! GA4 데이터 연동이 정상적으로 작동합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
테스트 결과: 최근 7일 세션 수 = {값}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 사용할 수 있습니다:
- 자연어로 질문: "이번 주 트래픽 소스 보여줘"
- 일일 브리핑: /smart-briefing:briefing
- 리포트 관리: /smart-briefing:reports
```

### 연결 실패 시

```
GA4 데이터 조회에 실패했습니다. 아래를 확인해주세요:

1. pipx가 설치되어 있는지: which pipx (없으면: brew install pipx)
2. 서비스 계정 JSON 파일 경로가 올바른지
3. GA4 Property ID가 올바른 숫자인지
4. 서비스 계정에 GA4 뷰어 권한이 있는지
5. Google Analytics Data API가 활성화되어 있는지

모두 확인 후 Claude Code를 재시작하고 다시 시도해주세요.
```
