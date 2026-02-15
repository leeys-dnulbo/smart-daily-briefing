#!/bin/bash
# SessionStart hook: SMART_BRIEFING_ROOT 환경변수를 주입합니다.
# ${CLAUDE_PLUGIN_ROOT}는 hooks.json에서 자동 치환되어 이 스크립트의 부모 디렉토리를 가리킵니다.
# CLAUDE_ENV_FILE에 export 구문을 기록하면, 이후 모든 Bash 도구 호출에서 사용 가능합니다.

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo "export SMART_BRIEFING_ROOT=\"$PLUGIN_ROOT\"" >> "$CLAUDE_ENV_FILE"
fi

# stdout으로 컨텍스트 주입 (Claude가 볼 수 있음)
echo "Smart Briefing 플러그인 경로: $PLUGIN_ROOT"
echo "차트 스크립트: $PLUGIN_ROOT/scripts/generate-charts.py"
echo "PDF 스크립트: $PLUGIN_ROOT/scripts/generate-pdf.py"

exit 0
