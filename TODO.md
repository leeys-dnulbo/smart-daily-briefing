# Smart Daily Briefing - 작업 현황

## 프로젝트 요약

GA4 데이터를 대화형으로 분석하는 Claude Code/Cowork 플러그인.
사용자가 "이번 주 세션 수 보여줘"라고 말하면 에이전트가 GA4 데이터를 조회/분석하고,
리포트 저장이나 정기 발송 스케줄까지 대화로 설정할 수 있다.

---

## 완료된 작업

### 플러그인 구조 (완료)
- [x] `.claude-plugin/plugin.json` - 매니페스트
- [x] `.claude-plugin/marketplace.json` - 마켓플레이스 배포 설정
- [x] `.mcp.json` - GA4 MCP 서버 (pipx run 자동설치)
- [x] `CLAUDE.md` - 자동 로드 컨텍스트 (MCP 미연결 감지)
- [x] `claude plugin validate .` 통과

### 스킬 (완료)
- [x] `skills/ga-analyst/SKILL.md` - 자연어 GA 질문 시 자동 데이터 조회/분석
- [x] `skills/report-manager/SKILL.md` - 리포트 저장/스케줄 요청 시 자동 처리

### 커맨드 (완료)
- [x] `/smart-briefing:setup` - 초기 설정 (환경변수 확인, GA4 연동 가이드, 연결 테스트)
- [x] `/smart-briefing:briefing` - 일일 종합 브리핑 생성 → `briefings/YYYY-MM-DD.md` 저장
- [x] `/smart-briefing:reports` - 저장된 리포트 목록 조회
- [x] `/smart-briefing:schedule` - 스케줄 조회/설정/즉시실행

### 인프라 (완료)
- [x] GitHub 레포 생성: https://github.com/leeys-dnulbo/smart-daily-briefing
- [x] `ga4-mcp-server` 로컬 설치 확인 (pipx, v2.0.0)
- [x] 로컬 테스트 (`claude --plugin-dir .`) - 커맨드 4개, 스킬 2개 인식 확인

---

## 진행 중

### Cowork 마켓플레이스 등록
- [x] `marketplace.json` 생성 및 검증 통과
- [x] `source` 경로 오류 수정 ("." → "./") 후 push
- [ ] **Cowork에서 마켓플레이스 추가 재시도 필요**
  - `/plugin marketplace add leeys-dnulbo/smart-daily-briefing`
  - 여전히 실패하면 marketplace.json 구조나 Cowork 호환성 문제 디버깅 필요

---

## 남은 작업

### 1순위: GA4 실제 연동 테스트
- [ ] 실제 Google Cloud 서비스 계정 JSON 준비
- [ ] 환경변수 설정 (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GA_PROPERTY_ID`)
- [ ] `/smart-briefing:setup` 으로 end-to-end 연결 확인
- [ ] 자연어 질문 → 실제 GA4 데이터 조회 확인
- [ ] `/smart-briefing:briefing` 으로 실제 브리핑 생성 확인

### 2순위: 스케줄 자동 실행
- [ ] 현재 `schedule` 필드는 JSON에 저장만 됨 (자동 실행 미구현)
- [ ] 방법 1: Claude Code hooks로 시작 시 스케줄 체크 → 자동 실행
- [ ] 방법 2: cron job + `claude -p "/smart-briefing:schedule run {name}"` 조합
- [ ] 방법 3: 스케줄은 안내만 하고 사용자가 직접 실행하도록 유지

### 3순위: 추가 기능
- [ ] 리포트 템플릿 프리셋 (트래픽 요약, 모바일 분석, 캠페인 리뷰 등)
- [ ] 브리핑 히스토리 비교 (어제 vs 오늘 브리핑 변화 추적)
- [ ] 알림 연동 (Slack, 이메일 등)
- [ ] 멀티 Property 지원 (여러 GA4 속성 동시 관리)

---

## 설치/실행 방법

### 마켓플레이스에서 설치 (Cowork / Claude Code)
```
/plugin marketplace add leeys-dnulbo/smart-daily-briefing
/plugin install smart-briefing@smart-daily-briefing
```

### 로컬에서 직접 실행
```bash
cd /Users/yunseop-lee/workspace/ga-agent-projects/smart-daily-briefing
claude --plugin-dir .
```

### 환경변수 (사용자가 각자 설정)
```bash
export GOOGLE_SERVICE_ACCOUNT_JSON="/path/to/service-account.json"
export GA_PROPERTY_ID="123456789"
```
