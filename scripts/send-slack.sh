#!/bin/bash
# Smart Daily Briefing - Slack 알림 전송 스크립트
# 사용법: send-slack.sh [YYYY-MM-DD | test]
# config.json의 notifications.slack.webhook_url이 설정된 경우만 동작합니다.

set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

DATE="${1:-$(date '+%Y-%m-%d')}"
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$PLUGIN_DIR/config.json"
BRIEFING_FILE="$PLUGIN_DIR/briefings/${DATE}.md"
LOG_FILE="$PLUGIN_DIR/briefings/schedule.log"

log() {
  if [ -d "$(dirname "$LOG_FILE")" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [slack] $1" >> "$LOG_FILE"
  fi
}

# config.json에서 Slack 설정 읽기
read_slack_config() {
  python3 -c "
import json, sys
try:
    with open('$CONFIG_FILE') as f:
        config = json.load(f)
    slack = config.get('notifications', {}).get('slack', {})
    url = slack.get('webhook_url', '')
    enabled = slack.get('enabled', True)
    if not url or not enabled:
        sys.exit(1)
    print(url)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

WEBHOOK_URL=$(read_slack_config) || {
  log "Slack webhook URL not configured or disabled. Skipping."
  exit 0
}

# 테스트 모드
if [ "$DATE" = "test" ]; then
  PAYLOAD=$(python3 -c "
import json
payload = {
    'blocks': [
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': ':white_check_mark: *Smart Daily Briefing* Slack 알림이 정상적으로 설정되었습니다.'
            }
        }
    ]
}
print(json.dumps(payload, ensure_ascii=False))
")

  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$WEBHOOK_URL")

  if [ "$HTTP_STATUS" = "200" ]; then
    log "Slack test message sent successfully."
    echo "OK: 테스트 메시지가 전송되었습니다."
  else
    log "ERROR: Slack test message failed (HTTP ${HTTP_STATUS})."
    echo "ERROR: 전송 실패 (HTTP ${HTTP_STATUS})"
    exit 1
  fi
  exit 0
fi

# 브리핑 파일 확인
if [ ! -f "$BRIEFING_FILE" ]; then
  log "ERROR: Briefing file not found: $BRIEFING_FILE"
  exit 1
fi

# 브리핑 파일에서 섹션 추출 및 Slack 페이로드 생성
PAYLOAD=$(python3 << 'PYEOF' "$DATE" "$BRIEFING_FILE"
import json, re, sys

date = sys.argv[1]
briefing_path = sys.argv[2]

with open(briefing_path, encoding="utf-8") as f:
    content = f.read()

def extract_section(md, heading):
    """## heading 과 다음 ## 사이의 내용을 추출"""
    pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, md, re.DOTALL)
    return m.group(1).strip() if m else ""

def truncate(text, limit=2800):
    if len(text) > limit:
        return text[:limit] + "\n..."
    return text

summary = extract_section(content, "핵심 요약")
metrics = extract_section(content, "주요 지표")
anomaly = extract_section(content, "이상 탐지")
insights = extract_section(content, "인사이트")
actions = extract_section(content, "액션 아이템")

# 메타 정보 추출
meta_match = re.search(r"> 프리셋: (.+?) \| 조회 기간: (.+)", content)
meta_text = f"프리셋: {meta_match.group(1)} | {meta_match.group(2)}" if meta_match else ""

blocks = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": f"GA 일일 브리핑 - {date}", "emoji": True}
    }
]

if summary:
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*핵심 요약*\n{truncate(summary)}"}
    })

if metrics:
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*주요 지표*\n{truncate(metrics)}"}
    })

if anomaly:
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*이상 탐지*\n{truncate(anomaly)}"}
    })

if actions:
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*액션 아이템*\n{truncate(actions)}"}
    })

if meta_text:
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": meta_text}]
    })

payload = {"blocks": blocks}
print(json.dumps(payload, ensure_ascii=False))
PYEOF
)

# Slack 전송
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK_URL")

if [ "$HTTP_STATUS" = "200" ]; then
  log "Slack notification sent successfully (${DATE})."
else
  log "ERROR: Slack notification failed (HTTP ${HTTP_STATUS})."
  exit 1
fi
