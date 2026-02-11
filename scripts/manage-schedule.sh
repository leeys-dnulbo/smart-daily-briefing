#!/bin/bash
# Smart Daily Briefing - 스케줄 관리 스크립트
# 사용법:
#   manage-schedule.sh install [HH:MM]
#   manage-schedule.sh uninstall
#   manage-schedule.sh install-report {name} {frequency} {time} [day]
#   manage-schedule.sh uninstall-report {name}
#   manage-schedule.sh status

set -euo pipefail

ACTION="${1:-}"
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$PLUGIN_DIR/briefings/schedule.log"

# 요일 이름 → launchd Weekday 숫자 변환 (0=일, 1=월, ..., 6=토)
day_to_weekday() {
  case "$1" in
    sunday|sun|일)    echo 0 ;;
    monday|mon|월)    echo 1 ;;
    tuesday|tue|화)   echo 2 ;;
    wednesday|wed|수) echo 3 ;;
    thursday|thu|목)  echo 4 ;;
    friday|fri|금)    echo 5 ;;
    saturday|sat|토)  echo 6 ;;
    *) echo "" ;;
  esac
}

# Weekday 숫자 → 한국어 요일
weekday_to_korean() {
  case "$1" in
    0) echo "일" ;; 1) echo "월" ;; 2) echo "화" ;; 3) echo "수" ;;
    4) echo "목" ;; 5) echo "금" ;; 6) echo "토" ;; *) echo "?" ;;
  esac
}

# Slack 상태 확인
check_slack_status() {
  python3 -c "
import json
try:
    with open('$PLUGIN_DIR/config.json') as f:
        c = json.load(f)
    s = c.get('notifications', {}).get('slack', {})
    if s.get('webhook_url') and s.get('enabled', True):
        print('ON')
    else:
        print('OFF')
except Exception:
    print('OFF')
" 2>/dev/null || echo "OFF"
}

case "$ACTION" in
  install)
    TIME="${2:-09:00}"
    HOUR="${TIME%%:*}"
    MINUTE="${TIME##*:}"
    PLIST_NAME="com.smart-briefing.daily"
    PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
    RUN_SCRIPT="$PLUGIN_DIR/scripts/run-briefing.sh"

    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$PLUGIN_DIR/briefings"

    # run-briefing.sh 생성
    cat > "$RUN_SCRIPT" << RUNSCRIPT
#!/bin/bash
# Smart Daily Briefing - 자동 브리핑 실행 스크립트
# 이 파일은 /smart-briefing:schedule install 에 의해 자동 생성됩니다.

PLUGIN_DIR="$PLUGIN_DIR"
LOG_FILE="\$PLUGIN_DIR/briefings/schedule.log"
TODAY=\$(date '+%Y-%m-%d')

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 시작" >> "\$LOG_FILE"

claude -p \\
  --plugin-dir "\$PLUGIN_DIR" \\
  "/smart-briefing:briefing" \\
  >> "\$LOG_FILE" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 완료" >> "\$LOG_FILE"

# Slack 알림 전송 (config.json에 webhook_url이 설정된 경우만)
if [ -f "\$PLUGIN_DIR/scripts/send-slack.sh" ]; then
  bash "\$PLUGIN_DIR/scripts/send-slack.sh" "\$TODAY" >> "\$LOG_FILE" 2>&1
fi
RUNSCRIPT
    chmod +x "$RUN_SCRIPT"

    # plist 생성
    cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_NAME</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUN_SCRIPT</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$HOUR</integer>
    <key>Minute</key>
    <integer>$MINUTE</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_FILE</string>
  <key>StandardErrorPath</key>
  <string>$LOG_FILE</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST

    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    echo "OK: 매일 ${TIME}에 브리핑이 실행됩니다."
    ;;

  uninstall)
    PLIST_NAME="com.smart-briefing.daily"
    PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
    RUN_SCRIPT="$PLUGIN_DIR/scripts/run-briefing.sh"

    if [ -f "$PLIST_PATH" ]; then
      launchctl unload "$PLIST_PATH" 2>/dev/null || true
      rm -f "$PLIST_PATH"
      rm -f "$RUN_SCRIPT"
      echo "OK: 스케줄이 제거되었습니다."
    else
      echo "NONE: 설정된 스케줄이 없습니다."
    fi
    ;;

  install-report)
    REPORT_NAME="${2:-}"
    FREQUENCY="${3:-daily}"
    REPORT_TIME="${4:-09:00}"
    DAY_OF_WEEK="${5:-}"
    R_HOUR="${REPORT_TIME%%:*}"
    R_MINUTE="${REPORT_TIME##*:}"

    if [ -z "$REPORT_NAME" ]; then
      echo "ERROR: 리포트 이름이 필요합니다."
      echo "사용법: manage-schedule.sh install-report {name} {frequency} {time} [day]"
      exit 1
    fi

    REPORT_PLIST_NAME="com.smart-briefing.report.${REPORT_NAME}"
    REPORT_PLIST_PATH="$HOME/Library/LaunchAgents/$REPORT_PLIST_NAME.plist"
    REPORT_RUN_SCRIPT="$PLUGIN_DIR/scripts/run-report-${REPORT_NAME}.sh"

    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$PLUGIN_DIR/briefings"

    # run-report-{name}.sh 생성
    cat > "$REPORT_RUN_SCRIPT" << RUNSCRIPT
#!/bin/bash
# Smart Daily Briefing - 리포트 자동 실행 스크립트
# 리포트: $REPORT_NAME
# 이 파일은 /smart-briefing:schedule 에 의해 자동 생성됩니다.

PLUGIN_DIR="$PLUGIN_DIR"
REPORT_NAME="$REPORT_NAME"
LOG_FILE="\$PLUGIN_DIR/briefings/schedule.log"
RESULT_FILE="\$PLUGIN_DIR/reports/\${REPORT_NAME}-latest.log"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 리포트 시작: \$REPORT_NAME" >> "\$LOG_FILE"

claude -p \\
  --plugin-dir "\$PLUGIN_DIR" \\
  "/smart-briefing:schedule run \$REPORT_NAME" \\
  > "\$RESULT_FILE" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 리포트 완료: \$REPORT_NAME" >> "\$LOG_FILE"

# Slack 알림 전송
if [ -f "\$PLUGIN_DIR/scripts/send-slack.sh" ]; then
  bash "\$PLUGIN_DIR/scripts/send-slack.sh" report "\$REPORT_NAME" >> "\$LOG_FILE" 2>&1
fi
RUNSCRIPT
    chmod +x "$REPORT_RUN_SCRIPT"

    # StartCalendarInterval 생성
    INTERVAL="    <key>Hour</key>\n    <integer>$R_HOUR</integer>\n    <key>Minute</key>\n    <integer>$R_MINUTE</integer>"

    if [ "$FREQUENCY" = "weekly" ] && [ -n "$DAY_OF_WEEK" ]; then
      WEEKDAY=$(day_to_weekday "$DAY_OF_WEEK")
      if [ -n "$WEEKDAY" ]; then
        INTERVAL="$INTERVAL\n    <key>Weekday</key>\n    <integer>$WEEKDAY</integer>"
      fi
    fi

    # plist 생성
    cat > "$REPORT_PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$REPORT_PLIST_NAME</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPORT_RUN_SCRIPT</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
$(printf "$INTERVAL")
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_FILE</string>
  <key>StandardErrorPath</key>
  <string>$LOG_FILE</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST

    launchctl unload "$REPORT_PLIST_PATH" 2>/dev/null || true
    launchctl load "$REPORT_PLIST_PATH"

    case "$FREQUENCY" in
      daily)  echo "OK: 리포트 '$REPORT_NAME'이(가) 매일 ${REPORT_TIME}에 실행됩니다." ;;
      weekly) echo "OK: 리포트 '$REPORT_NAME'이(가) 매주 ${DAY_OF_WEEK} ${REPORT_TIME}에 실행됩니다." ;;
      *)      echo "OK: 리포트 '$REPORT_NAME'이(가) ${REPORT_TIME}에 실행됩니다." ;;
    esac
    ;;

  uninstall-report)
    REPORT_NAME="${2:-}"
    if [ -z "$REPORT_NAME" ]; then
      echo "ERROR: 리포트 이름이 필요합니다."
      exit 1
    fi

    REPORT_PLIST_PATH="$HOME/Library/LaunchAgents/com.smart-briefing.report.${REPORT_NAME}.plist"
    REPORT_RUN_SCRIPT="$PLUGIN_DIR/scripts/run-report-${REPORT_NAME}.sh"

    if [ -f "$REPORT_PLIST_PATH" ]; then
      launchctl unload "$REPORT_PLIST_PATH" 2>/dev/null || true
      rm -f "$REPORT_PLIST_PATH"
      rm -f "$REPORT_RUN_SCRIPT"
      rm -f "$PLUGIN_DIR/reports/${REPORT_NAME}-latest.log"
      echo "OK: 리포트 '$REPORT_NAME' 스케줄이 제거되었습니다."
    else
      echo "NONE: '$REPORT_NAME' 스케줄이 설정되어 있지 않습니다."
    fi
    ;;

  status)
    # 일일 브리핑 상태
    PLIST_NAME="com.smart-briefing.daily"
    PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

    if [ -f "$PLIST_PATH" ]; then
      SCHED_HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$PLIST_PATH" 2>/dev/null)
      SCHED_MIN=$(plutil -extract StartCalendarInterval.Minute raw "$PLIST_PATH" 2>/dev/null)
      printf "ACTIVE: 매일 %02d:%02d\n" "$SCHED_HOUR" "$SCHED_MIN"
    else
      echo "NONE: 일일 브리핑 스케줄이 없습니다."
    fi

    # Slack 상태
    SLACK_STATUS=$(check_slack_status)
    if [ "$SLACK_STATUS" = "ON" ]; then
      echo "SLACK: 활성화됨"
    else
      echo "SLACK: 미설정"
    fi

    # 리포트 스케줄 상태
    REPORT_COUNT=0
    for rplist in "$HOME/Library/LaunchAgents/com.smart-briefing.report."*.plist; do
      [ -f "$rplist" ] || continue
      REPORT_COUNT=$((REPORT_COUNT + 1))
      if [ "$REPORT_COUNT" -eq 1 ]; then
        echo "REPORTS:"
      fi
      # 리포트 이름 추출
      RNAME=$(basename "$rplist" .plist | sed 's/com.smart-briefing.report.//')
      R_HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$rplist" 2>/dev/null || echo "?")
      R_MIN=$(plutil -extract StartCalendarInterval.Minute raw "$rplist" 2>/dev/null || echo "?")
      R_WEEKDAY=$(plutil -extract StartCalendarInterval.Weekday raw "$rplist" 2>/dev/null) || R_WEEKDAY=""
      if [ -n "$R_WEEKDAY" ]; then
        R_DAY_KR=$(weekday_to_korean "$R_WEEKDAY")
        printf "  %s | weekly | %s %02d:%02d\n" "$RNAME" "$R_DAY_KR" "$R_HOUR" "$R_MIN"
      else
        printf "  %s | daily | %02d:%02d\n" "$RNAME" "$R_HOUR" "$R_MIN"
      fi
    done

    if [ "$REPORT_COUNT" -eq 0 ]; then
      echo "REPORTS: 없음"
    fi

    # 마지막 실행 로그
    if [ -f "$LOG_FILE" ]; then
      LAST_LINE=$(tail -1 "$LOG_FILE" 2>/dev/null || echo "")
      if [ -n "$LAST_LINE" ]; then
        echo "LAST_RUN: $LAST_LINE"
      fi
    fi
    ;;

  *)
    echo "사용법:"
    echo "  manage-schedule.sh install [HH:MM]                              일일 브리핑 스케줄"
    echo "  manage-schedule.sh uninstall                                    일일 브리핑 해제"
    echo "  manage-schedule.sh install-report {name} {frequency} {time} [day]  리포트 스케줄"
    echo "  manage-schedule.sh uninstall-report {name}                      리포트 스케줄 해제"
    echo "  manage-schedule.sh status                                       전체 상태 확인"
    exit 1
    ;;
esac
