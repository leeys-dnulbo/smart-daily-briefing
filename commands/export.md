---
description: "[v2.0부터 briefing export로 통합] 브리핑을 PDF 파일로 내보냅니다."
argument-hint: "[YYYY-MM-DD | latest]"
---

# PDF 내보내기 (v2.0 마이그레이션 안내)

> 이 커맨드는 `/smart-briefing:briefing export`로 통합되었습니다.
> 기존과 동일하게 동작하지만, 향후 버전에서 제거될 예정입니다.

## 안내 메시지

먼저 다음 안내를 출력합니다:
```
[안내] /smart-briefing:export는 v2.0부터 /smart-briefing:briefing export로 통합되었습니다.
이번에는 정상적으로 실행하지만, 다음부터 아래 커맨드를 사용해주세요:
  /smart-briefing:briefing export {인수}
```

## 실행

이후 기존 export 로직을 그대로 실행합니다:

$ARGUMENTS

### 대상 브리핑 결정

인수에 따라 변환할 브리핑 파일을 결정합니다:

1. **날짜 지정** (예: `2026-02-15`): `briefings/2026-02-15.md` 파일을 사용합니다
2. **"latest" 또는 인수 없음**: `briefings/` 디렉토리에서 가장 최근 `.md` 파일을 찾습니다

### PDF 생성

```bash
PDF_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-pdf.py"
[ -z "$SMART_BRIEFING_ROOT" ] && PDF_SCRIPT=$(find "$HOME/.claude" "$HOME/Library/Application Support/Claude" -name "generate-pdf.py" -path "*smart-daily-briefing*" 2>/dev/null | head -1)
[ -z "$PDF_SCRIPT" ] && PDF_SCRIPT="scripts/generate-pdf.py"
PYTHON=$(command -v /opt/homebrew/bin/python3.13 || command -v /opt/homebrew/bin/python3.12 || command -v /opt/homebrew/bin/python3.11 || command -v python3) && \
$PYTHON "$PDF_SCRIPT" \
  --input briefings/{날짜}.md \
  --output briefings/{날짜}.pdf \
  --charts-dir briefings/charts/{날짜}/
```
