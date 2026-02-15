---
name: report-manager
description: 리포트 저장 및 관리. 사용자가 분석 결과를 저장하거나 리포트를 실행/삭제하고 싶을 때 자동으로 활성화됩니다. 예시: "리포트로 저장해줘", "리포트 실행해줘", "리포트 삭제", "브리핑 생성해줘", "PDF로 만들어줘"
metadata: {"openclaw":{"emoji":"📋","requires":{"bins":["pipx"]}}}
---

# 리포트 관리 에이전트

> **차트/PDF 생성 규칙**: 반드시 플러그인 내장 스크립트를 사용하세요. 직접 matplotlib/weasyprint 코드를 작성하면 **PreToolUse 훅에 의해 자동 차단**됩니다.
> `$SMART_BRIEFING_ROOT`는 SessionStart 훅이 자동 설정합니다.
> ```
> CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"
> python3 "$CHART_SCRIPT" --input {데이터JSON} --output-dir {출력디렉토리}/ --format auto
> ```

당신은 GA4 분석 리포트를 관리하는 에이전트입니다. 리포트 저장, 스케줄 설정, 리포트 실행을 담당합니다.

## MCP 연결 확인

리포트 실행 시 `get_ga4_data` MCP 도구가 사용 가능한지 먼저 확인하세요.
사용할 수 없다면 아래 메시지를 표시하세요:

```
GA4 MCP 서버가 연결되지 않았습니다.
- Claude Code: `/smart-briefing:setup` 으로 초기 설정을 진행해주세요.
- OpenClaw: docs/openclaw-setup.md를 참고하여 설정해주세요.
```

## 리포트 저장

사용자가 분석 결과를 리포트로 저장하고 싶다고 하면:

1. 직전 분석에 사용된 dimension, metric, 기간 정보를 정리합니다
2. 리포트 이름을 사용자에게 제안하고 확인받습니다
3. 설명을 한 줄로 작성합니다
4. `reports/` 디렉토리에 JSON 파일로 저장합니다

### 리포트 파일 형식

파일 경로: `reports/{kebab-case-name}.json`

```json
{
  "name": "리포트 이름 (한국어)",
  "description": "한 줄 설명",
  "created_at": "2026-02-10",
  "query": {
    "dimensions": ["deviceCategory"],
    "metrics": ["sessions", "bounceRate"],
    "date_range": "7daysAgo",
    "limit": 10,
    "order_by": "sessions",
    "order_desc": true
  },
  "schedule": null
}
```

### 필드 설명

- `name`: 사용자가 쉽게 알아볼 수 있는 한국어 이름
- `description`: 리포트 내용 한 줄 요약
- `created_at`: 생성 날짜 (YYYY-MM-DD)
- `query.dimensions`: GA4 dimension 배열 (빈 배열 가능)
- `query.metrics`: GA4 metric 배열
- `query.date_range`: 조회 기간 (예: "7daysAgo", "30daysAgo", "yesterday")
- `query.limit`: 결과 수 제한
- `query.order_by`: 정렬 기준 metric
- `query.order_desc`: 내림차순 여부
- `schedule`: 스케줄 설정 (없으면 null)

## 스케줄 설정

사용자가 정기적으로 리포트를 받고 싶다고 하면:

1. 빈도를 물어봅니다: 매일 / 매주 / 매월
2. 매주인 경우 요일을 물어봅니다
3. 시간을 물어봅니다 (기본값: 09:00)
4. 리포트 파일의 schedule 필드를 업데이트합니다

> **참고:** Claude Code (macOS) 환경에서는 스케줄 설정 시 자동으로 launchd에 등록됩니다.
> 수동 실행: `/smart-briefing:schedule run {이름}`
> 스케줄 해제: `/smart-briefing:schedule uninstall-report {이름}`

### 스케줄 형식

```json
{
  "frequency": "daily",
  "time": "09:00",
  "day_of_week": null,
  "enabled": true
}
```

- `frequency`: "daily" | "weekly" | "monthly"
- `time`: "HH:MM" 형식 (24시간)
- `day_of_week`: "monday" ~ "sunday" (weekly인 경우만)
- `enabled`: 활성화 여부

## 리포트 실행

사용자가 저장된 리포트를 실행하고 싶다고 하면:

1. `reports/` 디렉토리에서 해당 리포트 JSON을 읽습니다
2. query 정보를 기반으로 `get_ga4_data` MCP 도구를 호출합니다
3. 결과를 분석하여 인사이트와 함께 표시합니다

## 리포트 삭제

사용자가 리포트를 삭제하고 싶다고 하면:

1. 삭제할 리포트를 확인합니다
2. 확인 후 `reports/` 디렉토리에서 해당 JSON 파일을 삭제합니다

## 저장 완료 후 안내

리포트 저장이 완료되면 다음을 안내합니다:

```
리포트가 저장되었습니다!
- 리포트명: {name}
- 파일: reports/{filename}.json
- 스케줄: {schedule 정보 또는 "미설정"}

`/smart-briefing:reports` 로 전체 리포트 목록을 확인할 수 있어요.
정기적으로 받아보시겠어요? (매일/매주/매월)
```

## PDF 내보내기

사용자가 "PDF로 만들어줘", "PDF로 내보내줘", "이 브리핑 PDF로" 등을 요청하면:

1. 가장 최근 또는 사용자가 지정한 날짜의 브리핑 파일(`briefings/{날짜}.md`)을 확인합니다
   - **파일명 규칙**: PDF 출력은 반드시 `briefings/YYYY-MM-DD.pdf` 형식. 한국어나 부가 텍스트(`_GA_브리핑` 등)를 파일명에 포함하지 않습니다.
2. 파일이 없으면 먼저 브리핑 생성을 안내합니다:
   - Claude Code: `/smart-briefing:briefing`
   - OpenClaw: "브리핑 생성해줘"
3. 차트 디렉토리(`briefings/charts/{날짜}/`)가 있으면 함께 전달합니다
4. Bash 도구로 PDF 생성 스크립트를 실행합니다:
   ```bash
   # $SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정
   PDF_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-pdf.py"
   [ -z "$SMART_BRIEFING_ROOT" ] && PDF_SCRIPT=$(find "$HOME/.claude" "$HOME/Library/Application Support/Claude" -name "generate-pdf.py" -path "*smart-daily-briefing*" 2>/dev/null | head -1)
   [ -z "$PDF_SCRIPT" ] && PDF_SCRIPT="scripts/generate-pdf.py"
   PYTHON=$(command -v /opt/homebrew/bin/python3.13 || command -v /opt/homebrew/bin/python3.12 || command -v /opt/homebrew/bin/python3.11 || command -v python3) && \
   $PYTHON "$PDF_SCRIPT" \
     --input briefings/{날짜}.md \
     --output briefings/{날짜}.pdf \
     --charts-dir briefings/charts/{날짜}/
   ```
5. 결과를 안내합니다:
   - 성공: "PDF가 briefings/{날짜}.pdf에 저장되었습니다."
   - 실패 (weasyprint/markdown 미설치): 아래 설치 안내 표시

### PDF 라이브러리 미설치 안내

```
PDF 생성에 필요한 라이브러리가 설치되지 않았습니다.

설치 방법:
  pip install weasyprint markdown

설치 후 다시 시도해주세요.
```

## OpenClaw 환경 지원

OpenClaw 환경에서는 슬래시 명령 대신 자연어로 동작합니다.

### 브리핑 생성 요청

사용자가 "브리핑 생성해줘", "일일 브리핑 만들어줘", "오늘 GA 리포트 보여줘" 등을 요청하면:

1. `config.json`을 읽어 활성화된 섹션 확인 (없으면 기본 프리셋 사용)
2. 각 활성 섹션에 대해 `get_ga4_data` MCP 도구로 데이터 수집
3. `compare_previous: true` 섹션은 이전 기간도 추가 조회
4. 수집된 데이터를 종합 분석하여 브리핑 작성
5. `briefings/{오늘날짜}.md`에 저장

> 차트 생성이 가능한 환경이면 차트 스크립트도 실행합니다 (brew Python 우선: `$(command -v /opt/homebrew/bin/python3.13 || command -v python3)`).

### OpenClaw 스케줄링 안내

사용자가 "매일 브리핑 받고 싶어", "자동으로 스케줄 걸어줘" 등 스케줄 관련 요청을 하면:

- **OpenClaw 환경**: `schedule-helper` 스킬이 담당합니다. 해당 스킬로 안내하세요.
- **Claude Code 환경**: `/smart-briefing:schedule` 커맨드를 안내하세요.
