# Smart Daily Briefing

GA4 데이터를 대화형으로 분석하는 Claude Code 플러그인입니다.

## 플러그인 상태 확인

이 프로젝트가 로드되면 가장 먼저 GA4 MCP 서버 연결 상태를 확인하세요.
`ga4-analytics` 관련 MCP 도구(예: `mcp__ga4-analytics__get_ga4_data`)가 사용 가능한지 확인합니다.

MCP 도구가 사용 가능하지 않으면, 사용자에게 자동으로 안내하세요:

```
GA4 MCP 서버가 연결되지 않았습니다.

.mcp.json 파일이 있는지 확인해주세요:
- 없으면: cp .mcp.json.example .mcp.json 후 값을 입력하세요.
- 있으면: `/smart-briefing:setup` 으로 설정 상태를 점검하세요.
```

## 사용 가능한 기능

- 자연어 GA4 데이터 조회 및 분석 (ga-analyst 스킬)
- 분석 결과 리포트 저장 및 스케줄 관리 (report-manager 스킬)
- 브리핑 개인화 설정 (briefing-customizer 스킬)
- `/smart-briefing:briefing` - 일일 종합 브리핑 생성
- `/smart-briefing:customize` - 브리핑 설정 조회/변경
- `/smart-briefing:reports` - 저장된 리포트 목록
- `/smart-briefing:schedule` - 스케줄 관리
- `/smart-briefing:setup` - 초기 설정 안내

## 파일 저장 위치

- 리포트: `reports/*.json`
- 브리핑: `briefings/YYYY-MM-DD.md`
- 개인화 설정: `config.json`

## 응답 언어

사용자와 항상 한국어로 소통합니다.
