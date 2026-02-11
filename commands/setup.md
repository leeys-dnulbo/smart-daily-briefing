---
description: Smart Briefing 초기 설정을 안내합니다. GA4 MCP 서버 연결 상태를 확인하고 필요한 설정을 안내합니다.
---

# Smart Briefing 초기 설정

사용자의 GA4 연동 상태를 점검하고, 필요한 설정을 안내하세요.

## 1단계: MCP 서버 연결 확인

`ga4-analytics` 관련 MCP 도구(예: `get_ga4_data`, `search_schema`)가 사용 가능한지 확인하세요.

### MCP 도구가 있는 경우 → 2단계로 이동

### MCP 도구가 없는 경우

`.mcp.json` 파일이 프로젝트 루트에 존재하는지 확인하세요.

#### .mcp.json이 없는 경우

```
GA4 MCP 서버 설정이 필요합니다.

.mcp.json.example을 복사하여 .mcp.json을 생성하고, 실제 값을 입력해주세요:

  cp .mcp.json.example .mcp.json

그리고 .mcp.json 파일을 열어 아래 두 값을 수정하세요:
  - GOOGLE_APPLICATION_CREDENTIALS: 서비스 계정 JSON 파일의 절대 경로
  - GA4_PROPERTY_ID: GA4 속성 ID (숫자)
```

#### .mcp.json이 있지만 연결이 안 되는 경우

```
MCP 서버 설정은 있지만 연결되지 않았습니다. 아래를 확인해주세요:

1. pipx가 설치되어 있는지: which pipx (없으면: brew install pipx)
2. .mcp.json의 GOOGLE_APPLICATION_CREDENTIALS 경로에 파일이 실제로 존재하는지
3. .mcp.json의 GA4_PROPERTY_ID가 올바른 숫자인지
4. 서비스 계정에 GA4 뷰어 권한이 부여되어 있는지

모두 확인했으면 Claude Code를 재시작해보세요.
```

#### 서비스 계정이 아직 없는 경우

아래 가이드를 단계별로 안내하세요:

```
GA4 연동을 위해 두 가지가 필요합니다:

1. Google Cloud 서비스 계정 JSON 파일
2. GA4 Property ID

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

완료 후 .mcp.json에 값을 입력하고 Claude Code를 재시작하세요.
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

1. 서비스 계정 JSON 파일 경로가 올바른지
2. GA4 Property ID가 올바른 숫자인지
3. 서비스 계정에 GA4 뷰어 권한이 있는지
4. Google Analytics Data API가 활성화되어 있는지
```
