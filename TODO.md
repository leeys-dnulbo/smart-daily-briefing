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
- [x] `.mcp.json.example` - GA4 MCP 서버 설정 템플릿
- [x] `CLAUDE.md` - 자동 로드 컨텍스트 (MCP 미연결 감지)
- [x] `claude plugin validate .` 통과

### 스킬 (완료)
- [x] `skills/ga-analyst/SKILL.md` - 자연어 GA 질문 시 자동 데이터 조회/분석
- [x] `skills/report-manager/SKILL.md` - 리포트 저장/스케줄 요청 시 자동 처리
- [x] `skills/briefing-customizer/SKILL.md` - 브리핑 개인화 설정 (프리셋, 섹션 on/off, 임계값)

### 커맨드 (완료)
- [x] `/smart-briefing:setup` - 초기 설정 (.mcp.json 생성, GA4 연동 가이드, 연결 테스트)
- [x] `/smart-briefing:briefing` - 일일 종합 브리핑 생성 (config.json 기반 개인화)
- [x] `/smart-briefing:customize` - 브리핑 설정 조회/변경 (프리셋 적용, 리셋)
- [x] `/smart-briefing:reports` - 저장된 리포트 목록 조회
- [x] `/smart-briefing:schedule` - 스케줄 조회/설정/즉시실행

### 브리핑 개인화 (완료)
- [x] `config.json.example` - 설정 스키마 (9개 섹션, 5개 프리셋)
- [x] 프리셋: default, behavior, traffic, campaign, content
- [x] 자연어로 설정 변경 ("행동패턴 위주로 브리핑해줘")
- [x] 개별 섹션 on/off, 임계값/기간/인사이트 수 변경

### 에이전트 (완료)
- [x] `.claude/agents/` - 5개 서브에이전트 (planner, code-writer, code-reviewer, ga4-data-expert, plugin-tester)
- [x] `AGENTS.md` - 에이전트 아키텍처 문서

### 인프라 (완료)
- [x] GitHub 레포 생성: https://github.com/leeys-dnulbo/smart-daily-briefing
- [x] `ga4-mcp-server` 로컬 설치 확인 (pipx, v2.0.0)
- [x] 마켓플레이스 등록 및 플러그인 설치 확인
- [x] Claude Desktop 설정으로 Cowork MCP 연결

---

## 남은 작업

### 1순위: 스케줄 자동 실행
- [ ] 현재 `schedule` 필드는 JSON에 저장만 됨 (자동 실행 미구현)
- [ ] 사용자에게 자동 실행 미지원 사실을 명시적으로 안내
- [ ] 방법 1: Claude Code hooks로 시작 시 스케줄 체크 → 자동 실행
- [ ] 방법 2: cron job + `claude -p "/smart-briefing:schedule run {name}"` 조합

### 2순위: 추가 기능
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
claude --plugin-dir ./smart-daily-briefing
```

### MCP 설정
```bash
cp .mcp.json.example .mcp.json
# .mcp.json의 GOOGLE_APPLICATION_CREDENTIALS, GA4_PROPERTY_ID 값 수정
```
