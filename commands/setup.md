---
description: Smart Briefing 초기 설정을 안내합니다. GA4 연동에 필요한 환경변수와 MCP 서버 연결 상태를 확인합니다.
---

# Smart Briefing 초기 설정

사용자의 GA4 연동 상태를 점검하고, 필요한 설정을 안내하세요.
GA4 MCP 서버는 플러그인에 포함되어 있어 자동으로 설치/실행됩니다. 사용자가 해야 할 것은 환경변수 설정뿐입니다.

## 1단계: 환경변수 확인

터미널에서 아래 두 환경변수가 설정되어 있는지 확인하세요:

```bash
echo $GOOGLE_SERVICE_ACCOUNT_JSON
echo $GA_PROPERTY_ID
```

### 두 값 모두 있는 경우

```
환경변수가 설정되어 있습니다:
- GOOGLE_SERVICE_ACCOUNT_JSON: {경로}
- GA_PROPERTY_ID: {값}
```

다음으로 서비스 계정 JSON 파일이 실제로 존재하는지 확인하세요:

```bash
ls -la $GOOGLE_SERVICE_ACCOUNT_JSON
```

- 파일 존재: 2단계로 이동
- 파일 없음: "파일이 존재하지 않습니다. 경로를 확인해주세요." 안내

### 값이 없는 경우

아래 가이드를 단계별로 안내하세요:

```
GA4 연동을 위해 두 가지 설정이 필요합니다:

1. Google Cloud 서비스 계정 JSON 파일
2. GA4 Property ID

아직 서비스 계정이 없으시면 아래 절차를 따라주세요:

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

완료 후 셸 프로파일에 추가해주세요:

  echo 'export GOOGLE_SERVICE_ACCOUNT_JSON="/path/to/service-account.json"' >> ~/.zshrc
  echo 'export GA_PROPERTY_ID="123456789"' >> ~/.zshrc
  source ~/.zshrc

설정 후 Claude Code를 재시작하면 MCP 서버가 자동으로 연결됩니다.
```

## 2단계: MCP 서버 연결 테스트

MCP 도구 목록에서 `ga4-analytics` 관련 도구가 있는지 확인하세요.

### 연결 성공 시

간단한 테스트 쿼리를 실행하세요. `get_ga4_data` 도구로 최근 7일 세션 수를 조회합니다.

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
MCP 서버 연결에 실패했습니다. 아래를 확인해주세요:

1. pipx가 설치되어 있는지: which pipx (없으면: brew install pipx)
2. 환경변수가 설정되어 있는지: echo $GOOGLE_SERVICE_ACCOUNT_JSON
3. JSON 파일 경로가 올바른지: ls -la $GOOGLE_SERVICE_ACCOUNT_JSON
4. GA4 Property ID가 올바른지: echo $GA_PROPERTY_ID
5. 서비스 계정에 GA4 뷰어 권한이 있는지

모두 확인했는데도 안 되면, Claude Code를 재시작해보세요.
```
