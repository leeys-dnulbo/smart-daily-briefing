# Smart Daily Briefing - 작업 현황

## 프로젝트 요약

GA4 데이터를 대화형으로 분석하는 AI 에이전트 플러그인.
Claude Code와 OpenClaw 두 플랫폼에서 모두 사용 가능.

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
- [x] `skills/report-manager/SKILL.md` - 리포트 저장/스케줄 관리 + OpenClaw 브리핑 지원
- [x] `skills/briefing-customizer/SKILL.md` - 브리핑 개인화 설정 (프리셋, 섹션 on/off, 임계값)
- [x] `skills/schedule-helper/SKILL.md` - OpenClaw cron 스케줄 관리

### 커맨드 (완료)
- [x] `/smart-briefing:setup` - 초기 설정 (.mcp.json 생성, GA4 연동 가이드, 연결 테스트)
- [x] `/smart-briefing:briefing` - 일일 종합 브리핑 생성 (config.json 기반 개인화)
- [x] `/smart-briefing:customize` - 브리핑 설정 조회/변경 (프리셋 적용, 리셋)
- [x] `/smart-briefing:reports` - 저장된 리포트 목록 조회
- [x] `/smart-briefing:schedule` - 스케줄 조회/설정/즉시실행 (OpenClaw 환경 감지 포함)

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
- [x] 자동 브리핑 스케줄 (macOS launchd)
- [x] 리포트별 개별 스케줄 (launchd)
- [x] Slack 알림 연동 (웹훅)

### OpenClaw 연동 (완료 - Phase 1 & 2)
- [x] SKILL.md에 OpenClaw 메타데이터 추가 (3개 스킬)
- [x] `openclaw.json.example` - OpenClaw MCP 설정 템플릿
- [x] `docs/openclaw-setup.md` - OpenClaw 설치/설정 가이드
- [x] `skills/schedule-helper/SKILL.md` - OpenClaw cron 스케줄 관리 스킬
- [x] `commands/schedule.md` - 플랫폼 환경 감지 분기 추가
- [x] `report-manager` - OpenClaw 브리핑 생성 + cron 섹션 추가

---

## 남은 작업

### OpenClaw Phase 3: 멀티채널 알림 (보류)
- [ ] config.json에 `openclaw_channels` 스키마 추가
- [ ] briefing-customizer에 채널 관리 섹션 추가
- [ ] cron job 채널 전송 연동
- **블로커**: OpenClaw API 키 직렬화 취약점 (Issue #11202) 수정 대기

### OpenClaw Phase 4: 프로액티브 이상 탐지 (Phase 3 이후)
- [ ] `skills/anomaly-monitor/SKILL.md` 생성
- [ ] config.json에 monitoring 섹션 추가
- [ ] 4시간 주기 cron 모니터링 설정 안내

### OpenClaw Phase 5: 웹 크로스레퍼런스 (보류)
- [ ] 이상 탐지 시 자동 웹 검색으로 원인 파악
- **블로커**: 프롬프트 인젝션 보안 위험 (보류 권장)

### PDF 내보내기 (완료)
- [x] `scripts/generate-pdf.py` - 마크다운 → HTML → PDF 변환 (weasyprint)
- [x] `commands/export.md` - `/smart-briefing:export` 커맨드
- [x] `report-manager` - "PDF로 만들어줘" 자연어 트리거 지원
- [x] `briefing.md` - auto_pdf 기본 활성화 (config.json `export.auto_pdf`)
- [x] 차트 이미지 포함, 한국어 폰트 지원, A4 페이지 설정
- [x] PDF 파일명 `YYYY-MM-DD.pdf` 형식 강제

### 스크립트 인프라 (완료)
- [x] `hooks/inject-plugin-root.sh` - SessionStart 훅으로 `$SMART_BRIEFING_ROOT` 환경변수 주입
- [x] `hooks/validate-chart-code.py` - PreToolUse 훅으로 matplotlib/weasyprint 직접 사용 차단
- [x] `fonts/NanumGothic-Regular.ttf` - 컨테이너 환경용 번들 한국어 폰트
- [x] CFF-in-TTC 폰트 문제 해결 (AppleGothic.ttf 우선, FontProperties 직접 적용)
- [x] homebrew Python 자동 전환 (macOS)

### 추가 기능
- [ ] 브리핑 히스토리 비교 (어제 vs 오늘 변화 추적)
- [ ] 멀티 Property 지원 (여러 GA4 속성 동시 관리)
- [ ] ClawHub 마켓플레이스 등록

---

## 설치/실행 방법

### Claude Code에서 설치
```
/plugin marketplace add leeys-dnulbo/smart-daily-briefing
/plugin install smart-briefing@smart-daily-briefing
```

### 로컬에서 직접 실행
```bash
claude --plugin-dir ./smart-daily-briefing
```

### OpenClaw에서 설치
```
docs/openclaw-setup.md 참고
```

### MCP 설정
```bash
# Claude Code
cp .mcp.json.example .mcp.json

# OpenClaw
# openclaw.json에 mcpServers 섹션 추가 (openclaw.json.example 참고)
```
