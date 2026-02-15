# Smart Daily Briefing

GA4 데이터를 대화형으로 분석하는 AI 에이전트 플러그인입니다.
Claude Code와 OpenClaw 두 플랫폼에서 모두 사용할 수 있습니다.

## 플러그인 상태 확인

이 프로젝트가 로드되면 가장 먼저 GA4 MCP 서버 연결 상태를 확인하세요.
`ga4-analytics` 관련 MCP 도구(예: `mcp__ga4-analytics__get_ga4_data`)가 사용 가능한지 확인합니다.

MCP 도구가 사용 가능하지 않으면, 사용자에게 자동으로 안내하세요:

```
GA4 MCP 서버가 연결되지 않았습니다.

.mcp.json 파일이 있는지 확인해주세요:
- 없으면: cp .mcp.json.example .mcp.json 후 값을 입력하세요.
- 있으면: `/smart-briefing:setup` 으로 설정 상태를 점검하세요.

OpenClaw 사용자는 docs/openclaw-setup.md를 참고하세요.
```

## 사용 가능한 기능

### 스킬 (자동 트리거)
- 자연어 GA4 데이터 조회 및 분석 (ga-analyst)
- 분석 결과 리포트 저장 및 스케줄 관리 (report-manager)
- 브리핑 개인화 설정 (briefing-customizer)
- OpenClaw 스케줄 관리 (schedule-helper)

### 커맨드 (Claude Code 전용)
- `/smart-briefing:briefing` - 일일 종합 브리핑 생성
- `/smart-briefing:customize` - 브리핑 설정 조회/변경
- `/smart-briefing:reports` - 저장된 리포트 목록
- `/smart-briefing:schedule` - 스케줄 관리
- `/smart-briefing:export` - 브리핑 PDF 내보내기
- `/smart-briefing:setup` - 초기 설정 안내

## 파일 저장 위치

- 리포트: `reports/*.json`
- 브리핑: `briefings/YYYY-MM-DD.md` (PDF: `briefings/YYYY-MM-DD.pdf`)
- 개인화 설정: `config.json`

## 응답 언어

사용자와 항상 한국어로 소통합니다.

## CRITICAL: 차트/PDF 생성 규칙

**절대로 matplotlib/Python 차트 코드를 직접 작성하지 마세요.**
**반드시 플러그인에 포함된 `scripts/generate-charts.py` 스크립트를 실행해야 합니다.**

이 스크립트에는 한국어 폰트 자동 감지, 색상 팔레트, Python 자동 전환이 내장되어 있습니다.
직접 코드를 작성하면 한글이 깨지고 디자인이 일관되지 않습니다.

### 스크립트 경로

SessionStart 훅이 `$SMART_BRIEFING_ROOT` 환경변수를 자동 설정합니다.
모든 스크립트는 이 변수를 기준으로 참조하세요:

```bash
# $SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정
CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"
python3 "$CHART_SCRIPT" \
  --input briefings/charts/{날짜}/data.json \
  --output-dir briefings/charts/{날짜}/ \
  --format auto
```

PDF 생성도 동일:
```bash
PDF_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-pdf.py"
python3 "$PDF_SCRIPT" --input briefings/{날짜}.md --output briefings/{날짜}.pdf
```
