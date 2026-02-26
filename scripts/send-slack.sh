#!/bin/bash
# Smart Daily Briefing - Slack 알림 전송 스크립트
# 사용법:
#   send-slack.sh [YYYY-MM-DD]       브리핑 결과 전송
#   send-slack.sh test               테스트 메시지 전송
#   send-slack.sh report {name}      리포트 실행 결과 전송
# config.json의 notifications.slack.webhook_url이 설정된 경우만 동작합니다.

set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

DATE="${1:-$(date '+%Y-%m-%d')}"
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$PLUGIN_DIR/config.json"
BRIEFING_FILE="$PLUGIN_DIR/briefings/${DATE}.md"
LOG_FILE="$PLUGIN_DIR/briefings/schedule.log"
QUEUE_FILE="$PLUGIN_DIR/briefings/notification-queue.json"
LOCK_FILE="$PLUGIN_DIR/briefings/.notification-queue.lock"

MAX_RETRIES=3
MAX_QUEUE_SIZE=50

log() {
  if [ -d "$(dirname "$LOG_FILE")" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [slack] $1" >> "$LOG_FILE"
  fi
}

# ---------------------------------------------------------------------------
# flock shim: macOS does not ship flock. If the flock command is missing we
# fall back to a portable mkdir-based lock that is still safe against races.
# The shim exposes the same interface used below: flock -x <fd>  /  flock -u <fd>
# ---------------------------------------------------------------------------
if ! command -v flock >/dev/null 2>&1; then
  _lock_acquired=0

  _mkdir_lock() {
    local retries=0
    while ! mkdir "$LOCK_FILE.d" 2>/dev/null; do
      retries=$((retries + 1))
      # stale lock 감지: PID 파일이 있고 해당 프로세스가 없으면 제거
      if [ "$retries" -eq 10 ] && [ -f "$LOCK_FILE.d/pid" ]; then
        local old_pid
        old_pid=$(cat "$LOCK_FILE.d/pid" 2>/dev/null || echo "")
        if [ -n "$old_pid" ] && ! kill -0 "$old_pid" 2>/dev/null; then
          log "WARNING: Removing stale lock (pid=$old_pid)"
          rmdir "$LOCK_FILE.d" 2>/dev/null || rm -rf "$LOCK_FILE.d" 2>/dev/null
          continue
        fi
      fi
      if [ "$retries" -ge 30 ]; then
        log "WARNING: Could not acquire lock after 30 attempts"
        return 1
      fi
      sleep 0.1
    done
    # PID 기록
    echo $$ > "$LOCK_FILE.d/pid" 2>/dev/null || true
    _lock_acquired=1
    # Ensure the lock directory is removed on exit
    trap '_mkdir_unlock' EXIT
    return 0
  }

  _mkdir_unlock() {
    if [ "$_lock_acquired" -eq 1 ]; then
      rmdir "$LOCK_FILE.d" 2>/dev/null || true
      _lock_acquired=0
    fi
  }

  _FLOCK_SHIM=1
else
  _FLOCK_SHIM=0
fi

# ---------------------------------------------------------------------------
# with_queue_lock <command...>
#   Runs a command while holding an exclusive lock on the queue file.
# ---------------------------------------------------------------------------
with_queue_lock() {
  if [ "$_FLOCK_SHIM" -eq 1 ]; then
    _mkdir_lock || { log "WARNING: Proceeding without lock"; "$@"; return $?; }
    "$@"
    local rc=$?
    _mkdir_unlock
    return $rc
  else
    (
      flock -x 200 || { log "WARNING: Proceeding without lock"; "$@"; return $?; }
      "$@"
    ) 200>"$LOCK_FILE"
  fi
}

# ---------------------------------------------------------------------------
# send_with_retry <payload> <webhook_url>
#   Attempts to POST the payload up to MAX_RETRIES times with exponential
#   backoff (1s, 2s, 4s). Returns 0 on success, 1 on final failure.
#   On success, sets LAST_HTTP_STATUS to the HTTP code.
# ---------------------------------------------------------------------------
LAST_HTTP_STATUS=""

send_with_retry() {
  local payload="$1"
  local webhook_url="$2"
  local attempt=1
  local backoff=1

  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    # payload를 stdin으로 전달하여 셸 확장에 의한 인젝션 방지
    LAST_HTTP_STATUS=$(printf '%s' "$payload" | curl -s -o /dev/null -w "%{http_code}" \
      -X POST -H "Content-Type: application/json" \
      --data-binary @- \
      "$webhook_url") || LAST_HTTP_STATUS="000"

    if [ "$LAST_HTTP_STATUS" = "200" ]; then
      return 0
    fi

    log "Attempt $attempt/$MAX_RETRIES failed (HTTP ${LAST_HTTP_STATUS}). Retrying in ${backoff}s..."
    sleep "$backoff"
    attempt=$((attempt + 1))
    backoff=$((backoff * 2))
  done

  log "All $MAX_RETRIES attempts failed (last HTTP ${LAST_HTTP_STATUS})."
  return 1
}

# ---------------------------------------------------------------------------
# enqueue_payload <type> <payload>
#   Appends a message to the notification queue. Trims oldest entries if the
#   queue exceeds MAX_QUEUE_SIZE.
# ---------------------------------------------------------------------------
enqueue_payload() {
  local msg_type="$1"
  local payload="$2"

  _do_enqueue() {
    python3 << PYEOF "$QUEUE_FILE" "$msg_type" "$payload" "$MAX_QUEUE_SIZE"
import json, sys, os
from datetime import datetime, timezone

queue_file = sys.argv[1]
msg_type   = sys.argv[2]
payload    = sys.argv[3]
max_size   = int(sys.argv[4])

# Load existing queue
queue = []
if os.path.isfile(queue_file):
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue = json.load(f)
        if not isinstance(queue, list):
            queue = []
    except (json.JSONDecodeError, OSError):
        queue = []

# Parse the payload string back to a JSON object
try:
    payload_obj = json.loads(payload)
except json.JSONDecodeError:
    payload_obj = payload

# Append new entry
entry = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "type": msg_type,
    "payload": payload_obj
}
queue.append(entry)

# Trim to max size (drop oldest)
if len(queue) > max_size:
    queue = queue[-max_size:]

# Write atomically via temp file
tmp = queue_file + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(queue, f, ensure_ascii=False, indent=2)
os.replace(tmp, queue_file)

print(f"Queued. Total entries: {len(queue)}", file=sys.stderr)
PYEOF
  }

  with_queue_lock _do_enqueue
  log "Payload enqueued (type=$msg_type). Queue: $QUEUE_FILE"
}

# ---------------------------------------------------------------------------
# flush_queue <webhook_url>
#   If the queue file exists, attempts to send each queued message. Messages
#   that still fail are kept in the queue.
# ---------------------------------------------------------------------------
flush_queue() {
  local webhook_url="$1"

  [ -f "$QUEUE_FILE" ] || return 0

  _do_flush() {
    # Read the queue and try to send each entry. Write back only the failures.
    python3 << PYEOF "$QUEUE_FILE"
import json, sys, os

queue_file = sys.argv[1]

if not os.path.isfile(queue_file):
    sys.exit(0)

try:
    with open(queue_file, "r", encoding="utf-8") as f:
        queue = json.load(f)
except (json.JSONDecodeError, OSError):
    sys.exit(0)

if not isinstance(queue, list) or len(queue) == 0:
    sys.exit(0)

# Output each entry as a JSON line: {index}\t{payload_json}
for i, entry in enumerate(queue):
    payload = entry.get("payload", {})
    if isinstance(payload, str):
        print(f"{i}\t{payload}")
    else:
        print(f"{i}\t{json.dumps(payload, ensure_ascii=False)}")
PYEOF
  }

  local queue_lines
  queue_lines=$(with_queue_lock _do_flush 2>/dev/null) || return 0

  if [ -z "$queue_lines" ]; then
    return 0
  fi

  log "Flushing notification queue..."

  local failed_indices=""
  local total=0
  local sent=0

  while IFS=$'\t' read -r idx payload_json; do
    total=$((total + 1))
    if send_with_retry "$payload_json" "$webhook_url"; then
      sent=$((sent + 1))
      log "Queue entry #$idx sent successfully."
    else
      failed_indices="$failed_indices $idx"
      log "Queue entry #$idx still failing. Keeping in queue."
    fi
  done <<< "$queue_lines"

  # Rewrite queue keeping only failed entries
  _do_rewrite() {
    python3 << PYEOF "$QUEUE_FILE" "$failed_indices"
import json, sys, os

queue_file = sys.argv[1]
failed_raw = sys.argv[2].strip()

if not os.path.isfile(queue_file):
    sys.exit(0)

try:
    with open(queue_file, "r", encoding="utf-8") as f:
        queue = json.load(f)
except (json.JSONDecodeError, OSError):
    sys.exit(0)

if not failed_raw:
    # All succeeded - remove queue file
    os.remove(queue_file)
    sys.exit(0)

failed_set = set(int(x) for x in failed_raw.split())
remaining = [entry for i, entry in enumerate(queue) if i in failed_set]

if not remaining:
    os.remove(queue_file)
else:
    tmp = queue_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)
    os.replace(tmp, queue_file)

PYEOF
  }

  with_queue_lock _do_rewrite
  log "Queue flush complete: $sent/$total sent."
}

# ===========================================================================
# config.json에서 Slack 설정 읽기
# ===========================================================================
read_slack_config() {
  # 경로를 Python 인자로 전달하여 셸 인젝션 방지
  python3 - "$CONFIG_FILE" << 'PYEOF' 2>/dev/null
import json, sys
try:
    config_path = sys.argv[1]
    with open(config_path) as f:
        config = json.load(f)
    slack = config.get('notifications', {}).get('slack', {})
    url = slack.get('webhook_url', '')
    enabled = slack.get('enabled', True)
    if not url or not enabled:
        sys.exit(1)
    print(url)
except Exception:
    sys.exit(1)
PYEOF
}

WEBHOOK_URL=$(read_slack_config) || {
  log "Slack webhook URL not configured or disabled. Skipping."
  exit 0
}

# ===========================================================================
# Flush any previously queued messages before doing anything else.
# ===========================================================================
flush_queue "$WEBHOOK_URL"

# ===========================================================================
# 테스트 모드
# ===========================================================================
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

  if send_with_retry "$PAYLOAD" "$WEBHOOK_URL"; then
    log "Slack test message sent successfully."
    echo "OK: 테스트 메시지가 전송되었습니다."
  else
    enqueue_payload "test" "$PAYLOAD"
    log "ERROR: Slack test message failed after $MAX_RETRIES retries (HTTP ${LAST_HTTP_STATUS}). Queued for later."
    echo "ERROR: 전송 실패 (HTTP ${LAST_HTTP_STATUS}). 큐에 저장되었습니다."
    exit 1
  fi
  exit 0
fi

# ===========================================================================
# 리포트 모드
# ===========================================================================
if [ "$DATE" = "report" ]; then
  REPORT_NAME="${2:-}"
  if [ -z "$REPORT_NAME" ]; then
    log "ERROR: report mode requires report name."
    exit 1
  fi

  RESULT_FILE="$PLUGIN_DIR/reports/${REPORT_NAME}-latest.log"
  if [ ! -f "$RESULT_FILE" ]; then
    log "ERROR: Report result not found: $RESULT_FILE"
    exit 1
  fi

  PAYLOAD=$(python3 << 'PYEOF' "$REPORT_NAME" "$RESULT_FILE"
import json, sys

report_name = sys.argv[1]
result_path = sys.argv[2]

with open(result_path, encoding="utf-8") as f:
    content = f.read()

# 2800자로 제한
if len(content) > 2800:
    content = content[:2800] + "\n..."

blocks = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": f"리포트 실행 완료: {report_name}", "emoji": True}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": content}
    }
]

payload = {"blocks": blocks}
print(json.dumps(payload, ensure_ascii=False))
PYEOF
  )

  if send_with_retry "$PAYLOAD" "$WEBHOOK_URL"; then
    log "Slack report notification sent: $REPORT_NAME"
  else
    enqueue_payload "report" "$PAYLOAD"
    log "ERROR: Slack report notification failed after $MAX_RETRIES retries (HTTP ${LAST_HTTP_STATUS}). Queued for later."
    exit 1
  fi
  exit 0
fi

# ===========================================================================
# 브리핑 파일 확인
# ===========================================================================
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
if send_with_retry "$PAYLOAD" "$WEBHOOK_URL"; then
  log "Slack notification sent successfully (${DATE})."
else
  enqueue_payload "briefing" "$PAYLOAD"
  log "ERROR: Slack notification failed after $MAX_RETRIES retries (HTTP ${LAST_HTTP_STATUS}). Queued for later."
  exit 1
fi
