---
description: 브리핑을 PDF 파일로 내보냅니다. 날짜를 지정하거나 가장 최근 브리핑을 변환합니다.
argument-hint: [YYYY-MM-DD | latest]
---

# PDF 내보내기

$ARGUMENTS

브리핑 마크다운 파일을 PDF로 변환합니다.

## 동작

### 대상 브리핑 결정

인수에 따라 변환할 브리핑 파일을 결정합니다:

1. **날짜 지정** (예: `2026-02-15`): `briefings/2026-02-15.md` 파일을 사용합니다
2. **"latest" 또는 인수 없음**: `briefings/` 디렉토리에서 가장 최근 `.md` 파일을 찾습니다
   - Glob 도구로 `briefings/*.md` 패턴을 검색하여 가장 최근 파일 선택

### 파일 확인

대상 파일이 없으면:
```
해당 날짜의 브리핑이 없습니다.
`/smart-briefing:briefing`으로 먼저 생성하세요.
```

### PDF 생성

먼저 스크립트 위치를 찾고 실행합니다:

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

`--charts-dir`은 `briefings/charts/{날짜}/` 디렉토리가 존재하는 경우에만 전달합니다.

### 결과 안내

**성공 시:**
```
PDF가 생성되었습니다!
- 파일: briefings/{날짜}.pdf
- 크기: {파일크기}

원본 마크다운: briefings/{날짜}.md
```

**weasyprint 미설치 시** (종료코드 1, stderr에 "weasyprint" 포함):
```
PDF 생성에 필요한 라이브러리가 설치되지 않았습니다.

설치 방법:
  pip install weasyprint markdown

설치 후 다시 시도해주세요.
```

**markdown 미설치 시** (종료코드 1, stderr에 "markdown" 포함):
```
PDF 생성에 필요한 라이브러리가 설치되지 않았습니다.

설치 방법:
  pip install weasyprint markdown

설치 후 다시 시도해주세요.
```

**기타 오류 시:**
스크립트의 stderr 메시지를 표시합니다.
