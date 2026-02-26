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
LOG_FILE="${PLUGIN_DIR}/briefings/schedule.log"
PLATFORM="$(uname -s)"

# ---------------------------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------------------------

# HH:MM 형식 검증 (00-23:00-59)
validate_time() {
  local time="$1"
  if ! echo "$time" | grep -qE '^[0-9]{2}:[0-9]{2}$'; then
    echo "ERROR: 시간 형식이 올바르지 않습니다: ${time} (HH:MM 형식 필요)" >&2
    exit 1
  fi
  local hour="${time%%:*}"
  local minute="${time##*:}"
  # 10# 접두어로 08, 09 등의 8진수 해석 문제 방지
  if [ "$((10#$hour))" -gt 23 ]; then
    echo "ERROR: 시(hour)는 00-23 범위여야 합니다: ${hour}" >&2
    exit 1
  fi
  if [ "$((10#$minute))" -gt 59 ]; then
    echo "ERROR: 분(minute)은 00-59 범위여야 합니다: ${minute}" >&2
    exit 1
  fi
}

# 요일 이름 -> launchd Weekday 숫자 변환 (0=일, 1=월, ..., 6=토)
day_to_weekday() {
  local input
  input="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  case "$input" in
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

# Weekday 숫자 -> 한국어 요일
weekday_to_korean() {
  case "$1" in
    0) echo "일" ;; 1) echo "월" ;; 2) echo "화" ;; 3) echo "수" ;;
    4) echo "목" ;; 5) echo "금" ;; 6) echo "토" ;; *) echo "?" ;;
  esac
}

# XML 특수문자 이스케이프 (plist 생성 시 사용)
xml_escape() {
  printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g'
}

# Slack 상태 확인 (경로를 인자로 전달하여 인젝션 방지)
check_slack_status() {
  python3 - "${PLUGIN_DIR}/config.json" << 'PYEOF' 2>/dev/null || echo "OFF"
import json, sys
try:
    with open(sys.argv[1]) as f:
        c = json.load(f)
    s = c.get('notifications', {}).get('slack', {})
    if s.get('webhook_url') and s.get('enabled', True):
        print('ON')
    else:
        print('OFF')
except Exception:
    print('OFF')
PYEOF
}

# ---------------------------------------------------------------------------
# 실행 스크립트 생성 (중복 제거)
# 인자: script_path, script_content
# ---------------------------------------------------------------------------
generate_run_script() {
  local script_path="$1"
  local script_content="$2"

  printf '%s\n' "$script_content" > "$script_path"
  chmod +x "$script_path"
}

# ---------------------------------------------------------------------------
# macOS launchd plist 생성
# 인자: label, program_args, hour, minute [weekday]
# ---------------------------------------------------------------------------
generate_plist() {
  local label="$1"
  local program_args="$2"
  local hour="$3"
  local minute="$4"
  local weekday="${5:-}"

  local plist_path="${HOME}/Library/LaunchAgents/${label}.plist"
  mkdir -p "${HOME}/Library/LaunchAgents"

  # 8진수 리터럼 문제 방지: 선행 제로 제거
  local int_hour="$((10#$hour))"
  local int_minute="$((10#$minute))"

  # XML 특수문자 이스케이프
  local safe_label safe_args safe_log
  safe_label="$(xml_escape "$label")"
  safe_args="$(xml_escape "$program_args")"
  safe_log="$(xml_escape "$LOG_FILE")"

  local weekday_entry=""
  if [ -n "$weekday" ]; then
    weekday_entry="    <key>Weekday</key>
    <integer>${weekday}</integer>"
  fi

  cat > "$plist_path" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${safe_label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${safe_args}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${int_hour}</integer>
    <key>Minute</key>
    <integer>${int_minute}</integer>
${weekday_entry}  </dict>
  <key>StandardOutPath</key>
  <string>${safe_log}</string>
  <key>StandardErrorPath</key>
  <string>${safe_log}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST_EOF

  launchctl unload "$plist_path" 2>/dev/null || true
  launchctl load "$plist_path"
}

# ---------------------------------------------------------------------------
# Linux systemd timer/service 생성
# 인자: unit_name, program_args, hour, minute [weekday]
# ---------------------------------------------------------------------------
generate_systemd_timer() {
  local unit_name="$1"
  local program_args="$2"
  local hour="$3"
  local minute="$4"
  local weekday="${5:-}"

  local user_systemd_dir="${HOME}/.config/systemd/user"
  mkdir -p "$user_systemd_dir"

  local service_path="${user_systemd_dir}/${unit_name}.service"
  local timer_path="${user_systemd_dir}/${unit_name}.timer"

  # OnCalendar 스케줄 생성
  local on_calendar=""
  if [ -n "$weekday" ]; then
    # weekday(0=Sun..6=Sat) -> systemd 요일 약어
    local sd_day
    case "$weekday" in
      0) sd_day="Sun" ;; 1) sd_day="Mon" ;; 2) sd_day="Tue" ;; 3) sd_day="Wed" ;;
      4) sd_day="Thu" ;; 5) sd_day="Fri" ;; 6) sd_day="Sat" ;; *) sd_day="*" ;;
    esac
    on_calendar="${sd_day} *-*-* ${hour}:${minute}:00"
  else
    on_calendar="*-*-* ${hour}:${minute}:00"
  fi

  # .service 파일 생성
  cat > "$service_path" << SERVICE_EOF
[Unit]
Description=Smart Daily Briefing - ${unit_name}

[Service]
Type=oneshot
ExecStart=/bin/bash "${program_args}"
SERVICE_EOF

  # .timer 파일 생성
  cat > "$timer_path" << TIMER_EOF
[Unit]
Description=Timer for Smart Daily Briefing - ${unit_name}

[Timer]
OnCalendar=${on_calendar}
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

  systemctl --user daemon-reload
  systemctl --user enable --now "${unit_name}.timer"
}

# ---------------------------------------------------------------------------
# 플랫폼별 스케줄 등록
# 인자: label, program_args, hour, minute [weekday]
# ---------------------------------------------------------------------------
install_schedule() {
  local label="$1"
  local program_args="$2"
  local hour="$3"
  local minute="$4"
  local weekday="${5:-}"

  case "$PLATFORM" in
    Darwin)
      generate_plist "$label" "$program_args" "$hour" "$minute" "$weekday"
      ;;
    Linux)
      generate_systemd_timer "$label" "$program_args" "$hour" "$minute" "$weekday"
      ;;
    *)
      echo "ERROR: 지원되지 않는 플랫폼입니다: ${PLATFORM}" >&2
      exit 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# 플랫폼별 스케줄 제거
# 인자: label
# ---------------------------------------------------------------------------
uninstall_schedule() {
  local label="$1"

  case "$PLATFORM" in
    Darwin)
      local plist_path="${HOME}/Library/LaunchAgents/${label}.plist"
      if [ -f "$plist_path" ]; then
        launchctl unload "$plist_path" 2>/dev/null || true
        rm -f "$plist_path"
        return 0
      fi
      return 1
      ;;
    Linux)
      local user_systemd_dir="${HOME}/.config/systemd/user"
      local service_path="${user_systemd_dir}/${label}.service"
      local timer_path="${user_systemd_dir}/${label}.timer"
      if [ -f "$timer_path" ]; then
        systemctl --user disable --now "${label}.timer" 2>/dev/null || true
        rm -f "$service_path" "$timer_path"
        systemctl --user daemon-reload
        return 0
      fi
      return 1
      ;;
    *)
      echo "ERROR: 지원되지 않는 플랫폼입니다: ${PLATFORM}" >&2
      exit 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# 플랫폼별 스케줄 존재 확인
# 인자: label
# 반환: 존재하면 0, 아니면 1
# ---------------------------------------------------------------------------
schedule_exists() {
  local label="$1"

  case "$PLATFORM" in
    Darwin)
      [ -f "${HOME}/Library/LaunchAgents/${label}.plist" ]
      ;;
    Linux)
      [ -f "${HOME}/.config/systemd/user/${label}.timer" ]
      ;;
    *)
      return 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# 메인 case
# ---------------------------------------------------------------------------
case "$ACTION" in
  install)
    TIME="${2:-09:00}"
    validate_time "$TIME"
    HOUR="${TIME%%:*}"
    MINUTE="${TIME##*:}"
    PLIST_NAME="com.smart-briefing.daily"
    RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-briefing.sh"

    mkdir -p "${PLUGIN_DIR}/briefings"

    # run-briefing.sh 생성
    BRIEFING_CONTENT="$(cat << CONTENT_EOF
#!/bin/bash
# Smart Daily Briefing - 자동 브리핑 실행 스크립트
# 이 파일은 /smart-briefing:schedule install 에 의해 자동 생성됩니다.

PLUGIN_DIR="${PLUGIN_DIR}"
LOG_FILE="\${PLUGIN_DIR}/briefings/schedule.log"
TODAY=\$(date '+%Y-%m-%d')

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 시작" >> "\${LOG_FILE}"

claude -p \\
  --plugin-dir "\${PLUGIN_DIR}" \\
  "/smart-briefing:briefing" \\
  >> "\${LOG_FILE}" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 완료" >> "\${LOG_FILE}"

# Slack 알림 전송 (config.json에 webhook_url이 설정된 경우만)
if [ -f "\${PLUGIN_DIR}/scripts/send-slack.sh" ]; then
  bash "\${PLUGIN_DIR}/scripts/send-slack.sh" "\${TODAY}" >> "\${LOG_FILE}" 2>&1
fi
CONTENT_EOF
)"
    generate_run_script "$RUN_SCRIPT" "$BRIEFING_CONTENT"

    # 스케줄 등록
    install_schedule "$PLIST_NAME" "$RUN_SCRIPT" "$HOUR" "$MINUTE"
    echo "OK: 매일 ${TIME}에 브리핑이 실행됩니다."
    ;;

  uninstall)
    PLIST_NAME="com.smart-briefing.daily"
    RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-briefing.sh"

    if uninstall_schedule "$PLIST_NAME"; then
      rm -f "$RUN_SCRIPT"
      echo "OK: 스케줄이 제거되었습니다."
    else
      echo "NONE: 설정된 스케줄이 없습니다."
    fi
    ;;

  install-weekly)
    WEEKLY_TIME="${2:-09:00}"
    WEEKLY_DAY="${3:-monday}"
    validate_time "$WEEKLY_TIME"
    W_HOUR="${WEEKLY_TIME%%:*}"
    W_MINUTE="${WEEKLY_TIME##*:}"
    WEEKLY_WEEKDAY=$(day_to_weekday "$WEEKLY_DAY")
    if [ -z "$WEEKLY_WEEKDAY" ]; then
      echo "ERROR: 인식할 수 없는 요일입니다: ${WEEKLY_DAY}" >&2
      exit 1
    fi
    WEEKLY_PLIST="com.smart-briefing.weekly"
    WEEKLY_RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-weekly-briefing.sh"

    mkdir -p "${PLUGIN_DIR}/briefings"

    # run-weekly-briefing.sh 생성
    WEEKLY_CONTENT="$(cat << CONTENT_EOF
#!/bin/bash
# Smart Daily Briefing - 주간 브리핑 자동 실행 스크립트
# 이 파일은 /smart-briefing:schedule install-weekly 에 의해 자동 생성됩니다.

PLUGIN_DIR="${PLUGIN_DIR}"
LOG_FILE="\${PLUGIN_DIR}/briefings/schedule.log"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 주간 브리핑 시작" >> "\${LOG_FILE}"

claude -p \\
  --plugin-dir "\${PLUGIN_DIR}" \\
  "/smart-briefing:briefing weekly" \\
  >> "\${LOG_FILE}" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 주간 브리핑 완료" >> "\${LOG_FILE}"

# Slack 알림 전송
if [ -f "\${PLUGIN_DIR}/scripts/send-slack.sh" ]; then
  bash "\${PLUGIN_DIR}/scripts/send-slack.sh" "\$(date '+%Y-%m-%d')" >> "\${LOG_FILE}" 2>&1
fi
CONTENT_EOF
)"
    generate_run_script "$WEEKLY_RUN_SCRIPT" "$WEEKLY_CONTENT"

    # 스케줄 등록
    install_schedule "$WEEKLY_PLIST" "$WEEKLY_RUN_SCRIPT" "$W_HOUR" "$W_MINUTE" "$WEEKLY_WEEKDAY"
    WEEKLY_DAY_KR=$(weekday_to_korean "$WEEKLY_WEEKDAY")
    echo "OK: 매주 ${WEEKLY_DAY_KR}요일 ${WEEKLY_TIME}에 주간 브리핑이 실행됩니다."
    ;;

  uninstall-weekly)
    WEEKLY_PLIST="com.smart-briefing.weekly"
    WEEKLY_RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-weekly-briefing.sh"

    if uninstall_schedule "$WEEKLY_PLIST"; then
      rm -f "$WEEKLY_RUN_SCRIPT"
      echo "OK: 주간 브리핑 스케줄이 제거되었습니다."
    else
      echo "NONE: 주간 브리핑 스케줄이 없습니다."
    fi
    ;;

  install-report)
    REPORT_NAME="${2:-}"
    FREQUENCY="${3:-daily}"
    REPORT_TIME="${4:-09:00}"
    DAY_OF_WEEK="${5:-}"

    validate_time "$REPORT_TIME"
    R_HOUR="${REPORT_TIME%%:*}"
    R_MINUTE="${REPORT_TIME##*:}"

    if [ -z "$REPORT_NAME" ]; then
      echo "ERROR: 리포트 이름이 필요합니다."
      echo "사용법: manage-schedule.sh install-report {name} {frequency} {time} [day]"
      exit 1
    fi

    # 리포트 이름 검증 (영문, 숫자, 하이픈, 언더스코어만 허용)
    if ! echo "$REPORT_NAME" | grep -qE '^[a-zA-Z0-9_-]+$'; then
      echo "ERROR: 리포트 이름은 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용할 수 있습니다: ${REPORT_NAME}" >&2
      exit 1
    fi

    REPORT_LABEL="com.smart-briefing.report.${REPORT_NAME}"
    REPORT_RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-report-${REPORT_NAME}.sh"

    mkdir -p "${PLUGIN_DIR}/briefings"

    # run-report-{name}.sh 생성
    REPORT_CONTENT="$(cat << CONTENT_EOF
#!/bin/bash
# Smart Daily Briefing - 리포트 자동 실행 스크립트
# 리포트: ${REPORT_NAME}
# 이 파일은 /smart-briefing:schedule 에 의해 자동 생성됩니다.

PLUGIN_DIR="${PLUGIN_DIR}"
REPORT_NAME="${REPORT_NAME}"
LOG_FILE="\${PLUGIN_DIR}/briefings/schedule.log"
RESULT_FILE="\${PLUGIN_DIR}/reports/\${REPORT_NAME}-latest.log"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 리포트 시작: \${REPORT_NAME}" >> "\${LOG_FILE}"

claude -p \\
  --plugin-dir "\${PLUGIN_DIR}" \\
  "/smart-briefing:schedule run \${REPORT_NAME}" \\
  > "\${RESULT_FILE}" 2>&1

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 리포트 완료: \${REPORT_NAME}" >> "\${LOG_FILE}"

# Slack 알림 전송
if [ -f "\${PLUGIN_DIR}/scripts/send-slack.sh" ]; then
  bash "\${PLUGIN_DIR}/scripts/send-slack.sh" report "\${REPORT_NAME}" >> "\${LOG_FILE}" 2>&1
fi
CONTENT_EOF
)"
    generate_run_script "$REPORT_RUN_SCRIPT" "$REPORT_CONTENT"

    # 요일 처리
    WEEKDAY=""
    if [ "$FREQUENCY" = "weekly" ] && [ -n "$DAY_OF_WEEK" ]; then
      WEEKDAY=$(day_to_weekday "$DAY_OF_WEEK")
      if [ -z "$WEEKDAY" ]; then
        echo "ERROR: 인식할 수 없는 요일입니다: ${DAY_OF_WEEK}" >&2
        echo "사용 가능: sunday/sun/일, monday/mon/월, tuesday/tue/화, wednesday/wed/수, thursday/thu/목, friday/fri/금, saturday/sat/토" >&2
        exit 1
      fi
    fi

    # 스케줄 등록
    install_schedule "$REPORT_LABEL" "$REPORT_RUN_SCRIPT" "$R_HOUR" "$R_MINUTE" "$WEEKDAY"

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

    # 리포트 이름 검증 (install-report과 동일)
    if ! echo "$REPORT_NAME" | grep -qE '^[a-zA-Z0-9_-]+$'; then
      echo "ERROR: 리포트 이름은 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용할 수 있습니다: ${REPORT_NAME}" >&2
      exit 1
    fi

    REPORT_LABEL="com.smart-briefing.report.${REPORT_NAME}"
    REPORT_RUN_SCRIPT="${PLUGIN_DIR}/scripts/run-report-${REPORT_NAME}.sh"

    if uninstall_schedule "$REPORT_LABEL"; then
      rm -f "$REPORT_RUN_SCRIPT"
      rm -f "${PLUGIN_DIR}/reports/${REPORT_NAME}-latest.log"
      echo "OK: 리포트 '$REPORT_NAME' 스케줄이 제거되었습니다."
    else
      echo "NONE: '$REPORT_NAME' 스케줄이 설정되어 있지 않습니다."
    fi
    ;;

  status)
    # 일일 브리핑 상태
    PLIST_NAME="com.smart-briefing.daily"

    if schedule_exists "$PLIST_NAME"; then
      case "$PLATFORM" in
        Darwin)
          PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_NAME}.plist"
          SCHED_HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$PLIST_PATH" 2>/dev/null)
          SCHED_MIN=$(plutil -extract StartCalendarInterval.Minute raw "$PLIST_PATH" 2>/dev/null)
          printf "ACTIVE: 매일 %02d:%02d\n" "$SCHED_HOUR" "$SCHED_MIN"
          ;;
        Linux)
          TIMER_INFO=$(systemctl --user show "${PLIST_NAME}.timer" --property=TimersCalendar 2>/dev/null || echo "")
          echo "ACTIVE: ${TIMER_INFO:-스케줄 활성화됨}"
          ;;
      esac
    else
      echo "NONE: 일일 브리핑 스케줄이 없습니다."
    fi

    # 주간 브리핑 상태
    WEEKLY_PLIST="com.smart-briefing.weekly"
    if schedule_exists "$WEEKLY_PLIST"; then
      case "$PLATFORM" in
        Darwin)
          W_PLIST_PATH="${HOME}/Library/LaunchAgents/${WEEKLY_PLIST}.plist"
          W_HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$W_PLIST_PATH" 2>/dev/null)
          W_MIN=$(plutil -extract StartCalendarInterval.Minute raw "$W_PLIST_PATH" 2>/dev/null)
          W_WEEKDAY=$(plutil -extract StartCalendarInterval.Weekday raw "$W_PLIST_PATH" 2>/dev/null) || W_WEEKDAY=""
          if [ -n "$W_WEEKDAY" ]; then
            W_DAY_KR=$(weekday_to_korean "$W_WEEKDAY")
            printf "WEEKLY: 매주 %s요일 %02d:%02d\n" "$W_DAY_KR" "$W_HOUR" "$W_MIN"
          else
            printf "WEEKLY: %02d:%02d\n" "$W_HOUR" "$W_MIN"
          fi
          ;;
        Linux)
          W_TIMER_INFO=$(systemctl --user show "${WEEKLY_PLIST}.timer" --property=TimersCalendar 2>/dev/null || echo "")
          echo "WEEKLY: ${W_TIMER_INFO:-주간 스케줄 활성화됨}"
          ;;
      esac
    else
      echo "WEEKLY: 없음"
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
    case "$PLATFORM" in
      Darwin)
        for rplist in "${HOME}/Library/LaunchAgents/com.smart-briefing.report."*.plist; do
          [ -f "$rplist" ] || continue
          REPORT_COUNT=$((REPORT_COUNT + 1))
          if [ "$REPORT_COUNT" -eq 1 ]; then
            echo "REPORTS:"
          fi
          RNAME=$(basename "$rplist" .plist | sed 's/^com\.smart-briefing\.report\.//')
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
        ;;
      Linux)
        for rtimer in "${HOME}/.config/systemd/user/com.smart-briefing.report."*.timer; do
          [ -f "$rtimer" ] || continue
          REPORT_COUNT=$((REPORT_COUNT + 1))
          if [ "$REPORT_COUNT" -eq 1 ]; then
            echo "REPORTS:"
          fi
          RNAME=$(basename "$rtimer" .timer | sed 's/^com\.smart-briefing\.report\.//')
          TIMER_CAL=$(systemctl --user show "com.smart-briefing.report.${RNAME}.timer" --property=TimersCalendar 2>/dev/null || echo "?")
          printf "  %s | %s\n" "$RNAME" "$TIMER_CAL"
        done
        ;;
    esac

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
    echo "  manage-schedule.sh install-weekly [HH:MM] [요일]                주간 브리핑 스케줄"
    echo "  manage-schedule.sh uninstall-weekly                             주간 브리핑 해제"
    echo "  manage-schedule.sh install-report {name} {frequency} {time} [day]  리포트 스케줄"
    echo "  manage-schedule.sh uninstall-report {name}                      리포트 스케줄 해제"
    echo "  manage-schedule.sh status                                       전체 상태 확인"
    exit 1
    ;;
esac
