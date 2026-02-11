#!/bin/bash
# Smart Daily Briefing - 스케줄 관리 스크립트
# 사용법: manage-schedule.sh [install|uninstall|status] [HH:MM]

set -euo pipefail

ACTION="${1:-}"
TIME="${2:-09:00}"
HOUR="${TIME%%:*}"
MINUTE="${TIME##*:}"

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.smart-briefing.daily"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
RUN_SCRIPT="$PLUGIN_DIR/scripts/run-briefing.sh"
LOG_FILE="$PLUGIN_DIR/briefings/schedule.log"

case "$ACTION" in
  install)
    # LaunchAgents 디렉토리 확인
    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$PLUGIN_DIR/briefings"

    # run-briefing.sh 생성
    cat > "$RUN_SCRIPT" << RUNSCRIPT
#!/bin/bash
# Smart Daily Briefing - 자동 브리핑 실행 스크립트
# 이 파일은 /smart-briefing:schedule install 에 의해 자동 생성됩니다.

PLUGIN_DIR="$PLUGIN_DIR"
LOG_FILE="\$PLUGIN_DIR/briefings/schedule.log"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 시작" >> "\$LOG_FILE"

claude -p \\
  --plugin-dir "\$PLUGIN_DIR" \\
  "/smart-briefing:briefing" \\
  >> "\$LOG_FILE" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 완료" >> "\$LOG_FILE"
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

    # 기존 등록 해제 후 재등록
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    echo "OK: 매일 ${TIME}에 브리핑이 실행됩니다."
    ;;

  uninstall)
    if [ -f "$PLIST_PATH" ]; then
      launchctl unload "$PLIST_PATH" 2>/dev/null || true
      rm -f "$PLIST_PATH"
      rm -f "$RUN_SCRIPT"
      echo "OK: 스케줄이 제거되었습니다."
    else
      echo "NONE: 설정된 스케줄이 없습니다."
    fi
    ;;

  status)
    if [ -f "$PLIST_PATH" ]; then
      SCHED_HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$PLIST_PATH" 2>/dev/null)
      SCHED_MIN=$(plutil -extract StartCalendarInterval.Minute raw "$PLIST_PATH" 2>/dev/null)
      printf "ACTIVE: 매일 %02d:%02d\n" "$SCHED_HOUR" "$SCHED_MIN"
      if [ -f "$LOG_FILE" ]; then
        LAST_LINE=$(tail -1 "$LOG_FILE" 2>/dev/null || echo "")
        if [ -n "$LAST_LINE" ]; then
          echo "LAST_RUN: $LAST_LINE"
        fi
      fi
    else
      echo "NONE: 설정된 스케줄이 없습니다."
    fi
    ;;

  *)
    echo "사용법: manage-schedule.sh [install|uninstall|status] [HH:MM]"
    exit 1
    ;;
esac
