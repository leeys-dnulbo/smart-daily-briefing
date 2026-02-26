#!/usr/bin/env python3
"""
Smart Daily Briefing - 이상 탐지 모니터

브리핑 생성 후 sidecar JSON에서 이상 탐지 항목을 추출하고,
쿨다운/일일 한도를 적용하여 알림을 전송합니다.

Usage:
    python3 anomaly-monitor.py [YYYY-MM-DD]   # 해당 날짜 sidecar 분석
    python3 anomaly-monitor.py                 # 오늘 날짜 사용
    python3 anomaly-monitor.py history         # 알림 히스토리 조회
    python3 anomaly-monitor.py clear           # 히스토리 초기화

Exit codes:
    0 = 성공 (알림 전송 또는 전송 대상 없음)
    1 = 알림 전송 실패
    2 = 설정/파일 오류
"""

import json
import os
import sys
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------

def _find_plugin_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PLUGIN_DIR = _find_plugin_dir()
CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.json")
HISTORY_PATH = os.path.join(PLUGIN_DIR, "briefings", ".alert-history.json")
LOG_PATH = os.path.join(PLUGIN_DIR, "briefings", "schedule.log")

# 기본 설정
DEFAULT_COOLDOWN_HOURS = 24
DEFAULT_MAX_ALERTS_PER_DAY = 10


def log(message):
    """로그 파일에 기록."""
    log_dir = os.path.dirname(LOG_PATH)
    if os.path.isdir(log_dir):
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [anomaly] {message}\n")
        except OSError:
            pass


def load_config():
    """config.json 로드."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_alert_config(config):
    """알림 설정 추출."""
    alert = config.get("notifications", {}).get("anomaly_alerts", {})
    return {
        "enabled": alert.get("enabled", True),
        "cooldown_hours": alert.get("cooldown_hours", DEFAULT_COOLDOWN_HOURS),
        "max_alerts_per_day": alert.get("max_alerts_per_day", DEFAULT_MAX_ALERTS_PER_DAY),
        "min_severity": alert.get("min_severity", "warning"),
    }


# ---------------------------------------------------------------------------
# 히스토리 관리
# ---------------------------------------------------------------------------

def load_history():
    """알림 히스토리 로드."""
    if not os.path.exists(HISTORY_PATH):
        return {"alerts": []}
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "alerts" not in data:
            return {"alerts": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"alerts": []}


def save_history(history):
    """알림 히스토리 저장."""
    history_dir = os.path.dirname(HISTORY_PATH)
    if not os.path.isdir(history_dir):
        os.makedirs(history_dir, exist_ok=True)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError as e:
        log(f"Failed to save history: {e}")


def clean_old_history(history, days=7):
    """7일 이상 된 히스토리 항목 제거."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    history["alerts"] = [
        a for a in history["alerts"]
        if a.get("timestamp", "") >= cutoff
    ]
    return history


def count_today_alerts(history):
    """오늘 전송된 알림 수."""
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1 for a in history["alerts"]
        if a.get("timestamp", "").startswith(today)
    )


def is_in_cooldown(history, metric, cooldown_hours):
    """특정 메트릭이 쿨다운 기간 내인지 확인."""
    cutoff = (datetime.now() - timedelta(hours=cooldown_hours)).isoformat()
    for a in reversed(history["alerts"]):
        if a.get("metric") == metric and a.get("timestamp", "") >= cutoff:
            return True
    return False


def record_alert(history, metric, change_pct, severity):
    """알림 전송 기록."""
    history["alerts"].append({
        "metric": metric,
        "change_pct": change_pct,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    })
    return history


# ---------------------------------------------------------------------------
# 이상 탐지 필터링
# ---------------------------------------------------------------------------

SEVERITY_LEVELS = {"warning": 1, "critical": 2}


def filter_anomalies(anomalies, history, alert_config):
    """쿨다운, 일일 한도, 최소 심각도를 적용하여 알림 대상을 필터링."""
    min_level = SEVERITY_LEVELS.get(alert_config["min_severity"], 1)
    cooldown_hours = alert_config["cooldown_hours"]
    max_per_day = alert_config["max_alerts_per_day"]

    today_count = count_today_alerts(history)
    remaining = max_per_day - today_count
    if remaining <= 0:
        log(f"Daily alert limit reached ({max_per_day}). Skipping.")
        return []

    filtered = []
    for anomaly in anomalies:
        metric = anomaly.get("metric", "")
        severity = anomaly.get("severity", "warning")
        level = SEVERITY_LEVELS.get(severity, 1)

        # 심각도 필터
        if level < min_level:
            continue

        # 쿨다운 필터
        if is_in_cooldown(history, metric, cooldown_hours):
            log(f"Metric '{metric}' is in cooldown. Skipping.")
            continue

        filtered.append(anomaly)
        if len(filtered) >= remaining:
            break

    return filtered


# ---------------------------------------------------------------------------
# sidecar 분석
# ---------------------------------------------------------------------------

def load_sidecar(date):
    """해당 날짜 sidecar JSON 로드."""
    path = os.path.join(PLUGIN_DIR, "briefings", f"{date}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def extract_anomalies(sidecar):
    """sidecar에서 이상 탐지 항목을 추출."""
    if not isinstance(sidecar, dict):
        return []
    anomalies = sidecar.get("anomalies", [])
    if not isinstance(anomalies, list):
        return []
    return [a for a in anomalies if isinstance(a, dict)]


# ---------------------------------------------------------------------------
# 알림 전송
# ---------------------------------------------------------------------------

def send_anomaly_alert(anomalies):
    """send-notification.py를 통해 이상 탐지 알림을 전송."""
    import subprocess

    notification_script = os.path.join(PLUGIN_DIR, "scripts", "send-notification.py")
    if not os.path.exists(notification_script):
        log(f"send-notification.py not found: {notification_script}")
        return False

    anomalies_json = json.dumps(anomalies, ensure_ascii=False)
    try:
        result = subprocess.run(
            [sys.executable, notification_script, "anomaly", anomalies_json],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"Failed to run send-notification.py: {e}")
        return False


# ---------------------------------------------------------------------------
# CLI 액션
# ---------------------------------------------------------------------------

def action_monitor(date=None):
    """메인 모니터링 로직."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    config = load_config()
    alert_config = get_alert_config(config)

    if not alert_config["enabled"]:
        log("Anomaly alerts disabled.")
        print("이상 탐지 알림이 비활성화되어 있습니다.")
        return 0

    sidecar = load_sidecar(date)
    if sidecar is None:
        log(f"Sidecar not found for {date}.")
        print(f"sidecar 파일을 찾을 수 없습니다: briefings/{date}.json", file=sys.stderr)
        return 2

    anomalies = extract_anomalies(sidecar)
    if not anomalies:
        log(f"No anomalies in {date} sidecar.")
        print("이상 탐지 항목이 없습니다.")
        return 0

    history = load_history()
    history = clean_old_history(history)

    filtered = filter_anomalies(anomalies, history, alert_config)
    if not filtered:
        log("No anomalies after filtering (cooldown/limit/severity).")
        print("필터링 후 알림 대상이 없습니다 (쿨다운/한도/심각도).")
        return 0

    # 알림 전송
    if send_anomaly_alert(filtered):
        log(f"Anomaly alert sent: {len(filtered)} items.")
        for a in filtered:
            history = record_alert(
                history, a.get("metric", ""), a.get("change_pct", 0), a.get("severity", "warning")
            )
        save_history(history)
        print(f"이상 탐지 알림 전송: {len(filtered)}건")
        return 0
    else:
        log("Anomaly alert send failed.")
        print("이상 탐지 알림 전송 실패", file=sys.stderr)
        return 1


def action_history():
    """히스토리 조회."""
    history = load_history()
    alerts = history.get("alerts", [])
    if not alerts:
        print("알림 히스토리가 없습니다.")
        return 0

    print(f"이상 탐지 알림 히스토리 ({len(alerts)}건):")
    print()
    for a in reversed(alerts[-20:]):  # 최근 20개
        ts = a.get("timestamp", "?")[:19]
        metric = a.get("metric", "?")
        change = a.get("change_pct", 0)
        severity = a.get("severity", "?")
        direction = "+" if change > 0 else ""
        print(f"  [{ts}] {metric}: {direction}{change:.1f}% ({severity})")
    return 0


def action_clear():
    """히스토리 초기화."""
    save_history({"alerts": []})
    log("Alert history cleared.")
    print("알림 히스토리가 초기화되었습니다.")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        return action_monitor()

    arg = sys.argv[1]
    if arg == "history":
        return action_history()
    elif arg == "clear":
        return action_clear()
    else:
        # YYYY-MM-DD 날짜로 간주
        return action_monitor(arg)


if __name__ == "__main__":
    sys.exit(main())
