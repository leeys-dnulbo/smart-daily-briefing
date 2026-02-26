#!/usr/bin/env python3
"""
Smart Daily Briefing - Python 통합 알림 시스템

v1.12.0에서 도입. send-slack.sh를 대체하는 순수 Python 구현.
외부 의존성 없음 (urllib.request 사용).

Usage:
    python3 send-notification.py briefing [YYYY-MM-DD]   # 브리핑 알림
    python3 send-notification.py test                     # 테스트 메시지
    python3 send-notification.py anomaly <json>           # 이상 탐지 알림
    python3 send-notification.py flush                    # 실패 큐 재전송
    python3 send-notification.py status                   # 채널 상태 확인

Exit codes:
    0 = 성공
    1 = 전송 실패 (큐에 저장됨)
    2 = 설정 오류
"""

import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------

def _find_plugin_dir():
    """스크립트 위치 기반으로 플러그인 디렉토리를 찾는다."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PLUGIN_DIR = _find_plugin_dir()
CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.json")
QUEUE_PATH = os.path.join(PLUGIN_DIR, "briefings", "notification-queue.json")
LOG_PATH = os.path.join(PLUGIN_DIR, "briefings", "schedule.log")

MAX_RETRIES = 3
MAX_QUEUE_SIZE = 50
MAX_FLUSH_RETRIES = 10


def log(message, channel="notify"):
    """로그 파일에 기록."""
    log_dir = os.path.dirname(LOG_PATH)
    if os.path.isdir(log_dir):
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{channel}] {message}\n")
        except OSError:
            pass


def load_config():
    """config.json을 로드한다. 없으면 빈 dict."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# 채널 추상화
# ---------------------------------------------------------------------------

class NotificationChannel:
    """알림 채널 인터페이스.

    v2.0.0에서 TelegramChannel, DiscordChannel 추가 시 이 클래스를 상속.
    """
    name = ""

    def is_configured(self, config):
        """채널이 설정되어 있는지 확인."""
        raise NotImplementedError

    def send(self, payload, config):
        """메시지를 전송. 성공 시 True, 실패 시 False."""
        raise NotImplementedError

    def build_test_payload(self):
        """테스트 메시지 페이로드 생성."""
        raise NotImplementedError

    def build_briefing_payload(self, date, content):
        """브리핑 알림 페이로드 생성."""
        raise NotImplementedError

    def build_anomaly_payload(self, anomalies):
        """이상 탐지 알림 페이로드 생성."""
        raise NotImplementedError


class SlackChannel(NotificationChannel):
    """Slack Incoming Webhook 채널."""
    name = "slack"

    def is_configured(self, config):
        slack = config.get("notifications", {}).get("slack", {})
        url = slack.get("webhook_url", "")
        enabled = slack.get("enabled", True)
        return bool(url) and enabled and url.startswith("https://")

    def _get_webhook_url(self, config):
        return config.get("notifications", {}).get("slack", {}).get("webhook_url", "")

    def send(self, payload, config):
        url = self._get_webhook_url(config)
        if not url or not url.startswith("https://"):
            return False
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def build_test_payload(self):
        return {
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":white_check_mark: *Smart Daily Briefing* 알림이 정상적으로 설정되었습니다.",
                },
            }]
        }

    def build_briefing_payload(self, date, content):
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"GA 일일 브리핑 - {date}", "emoji": True},
            }
        ]

        sections = [
            ("핵심 요약", "핵심 요약"),
            ("주요 지표", "주요 지표"),
            ("이상 탐지", "이상 탐지"),
            ("인사이트", "인사이트"),
            ("액션 아이템", "액션 아이템"),
        ]
        for heading, label in sections:
            text = _extract_section(content, heading)
            if text:
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{label}*\n{_truncate(text)}"},
                })

        meta = re.search(r"> 프리셋: (.+?) \| 조회 기간: (.+)", content)
        if meta:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"프리셋: {meta.group(1)} | {meta.group(2)}"}],
            })

        return {"blocks": blocks}

    def build_anomaly_payload(self, anomalies):
        if not anomalies:
            return None
        lines = [":warning: *이상 탐지 알림*", ""]
        for a in anomalies:
            metric = a.get("metric", "?")
            change = a.get("change_pct", 0)
            try:
                change = float(change)
            except (TypeError, ValueError):
                change = 0.0
            severity = a.get("severity", "warning")
            icon = ":rotating_light:" if severity == "critical" else ":warning:"
            direction = "+" if change > 0 else ""
            lines.append(f"{icon} *{metric}*: {direction}{change:.1f}% ({severity})")
        return {
            "blocks": [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            }]
        }


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------

def _extract_section(md, heading):
    """마크다운에서 ## heading 섹션 내용을 추출."""
    pattern = rf"##\s+{re.escape(heading)}[ \t]*\r?\n(.*?)(?=\r?\n##\s|\Z)"
    m = re.search(pattern, md, re.DOTALL)
    return m.group(1).strip() if m else ""


def _truncate(text, limit=2800):
    if len(text) > limit:
        return text[:limit] + "\n..."
    return text


# ---------------------------------------------------------------------------
# 전송 + 재시도 + 큐
# ---------------------------------------------------------------------------

def send_with_retry(channel, payload, config, max_retries=MAX_RETRIES):
    """재시도 로직 포함 전송. 성공 시 True."""
    backoff = 1
    for attempt in range(1, max_retries + 1):
        if channel.send(payload, config):
            return True
        if attempt < max_retries:
            log(f"Attempt {attempt}/{max_retries} failed. Retrying in {backoff}s...", channel.name)
            time.sleep(backoff)
            backoff *= 2
    log(f"All {max_retries} attempts failed.", channel.name)
    return False


def enqueue(msg_type, payload):
    """실패한 메시지를 큐에 저장."""
    queue = []
    if os.path.exists(QUEUE_PATH):
        try:
            with open(QUEUE_PATH, encoding="utf-8") as f:
                queue = json.load(f)
            if not isinstance(queue, list):
                queue = []
        except (json.JSONDecodeError, OSError):
            queue = []

    entry = {
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.now().isoformat(),
        "retries": 0,
    }
    queue.append(entry)

    # 큐 크기 제한
    if len(queue) > MAX_QUEUE_SIZE:
        queue = queue[-MAX_QUEUE_SIZE:]

    queue_dir = os.path.dirname(QUEUE_PATH)
    if not os.path.isdir(queue_dir):
        os.makedirs(queue_dir, exist_ok=True)

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=queue_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        os.replace(tmp, QUEUE_PATH)
        tmp = None  # 성공 시 정리 불필요
    except OSError as e:
        log(f"Failed to write queue: {e}")
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def flush_queue(channel, config):
    """큐에 쌓인 메시지를 재전송."""
    if not os.path.exists(QUEUE_PATH):
        return 0, 0

    try:
        with open(QUEUE_PATH, encoding="utf-8") as f:
            queue = json.load(f)
        if not isinstance(queue, list):
            return 0, 0
    except (json.JSONDecodeError, OSError):
        return 0, 0

    if not queue:
        return 0, 0

    sent = 0
    failed = []
    for entry in queue:
        retries = entry.get("retries", 0)
        if retries >= MAX_FLUSH_RETRIES:
            log(f"Dropping message after {retries} retries (type={entry.get('type', '?')})", channel.name)
            continue
        payload = entry.get("payload", {})
        if channel.send(payload, config):
            sent += 1
            log(f"Flushed queued message (type={entry.get('type', '?')})", channel.name)
        else:
            entry["retries"] = retries + 1
            failed.append(entry)

    # atomic 재작성
    tmp = None
    try:
        queue_dir = os.path.dirname(QUEUE_PATH)
        fd, tmp = tempfile.mkstemp(dir=queue_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        os.replace(tmp, QUEUE_PATH)
        tmp = None
    except OSError as e:
        log(f"Failed to update queue file after flush: {e}", channel.name)
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass

    return sent, len(failed)


# ---------------------------------------------------------------------------
# NotificationRouter
# ---------------------------------------------------------------------------

# 채널 레지스트리: v2.0.0에서 Telegram/Discord 추가
CHANNELS = {
    "slack": SlackChannel(),
}


def get_active_channels(config):
    """설정된 활성 채널 목록을 반환."""
    return [ch for ch in CHANNELS.values() if ch.is_configured(config)]


def get_channel_status(config):
    """각 채널의 상태를 반환."""
    statuses = {}
    for key, ch in CHANNELS.items():
        configured = ch.is_configured(config)
        statuses[key] = {
            "name": ch.name,
            "configured": configured,
        }
    # 큐 상태
    queue_size = 0
    if os.path.exists(QUEUE_PATH):
        try:
            with open(QUEUE_PATH, encoding="utf-8") as f:
                queue_size = len(json.load(f))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    statuses["_queue"] = {"pending": queue_size}
    return statuses


# ---------------------------------------------------------------------------
# CLI 액션
# ---------------------------------------------------------------------------

def action_test(config):
    """테스트 메시지 전송."""
    channels = get_active_channels(config)
    if not channels:
        print("설정된 알림 채널이 없습니다.", file=sys.stderr)
        return 2

    ok = True
    for ch in channels:
        payload = ch.build_test_payload()
        if send_with_retry(ch, payload, config):
            log("Test message sent.", ch.name)
            print(f"[{ch.name}] 테스트 메시지 전송 성공")
        else:
            log("Test message failed.", ch.name)
            print(f"[{ch.name}] 테스트 메시지 전송 실패", file=sys.stderr)
            ok = False
    return 0 if ok else 1


def action_briefing(config, date=None):
    """브리핑 알림 전송."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print(f"유효하지 않은 날짜 형식: {date} (YYYY-MM-DD)", file=sys.stderr)
        return 2

    briefing_path = os.path.join(PLUGIN_DIR, "briefings", f"{date}.md")
    if not os.path.exists(briefing_path):
        log(f"Briefing file not found: {briefing_path}")
        print(f"브리핑 파일을 찾을 수 없습니다: {briefing_path}", file=sys.stderr)
        return 1

    try:
        with open(briefing_path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        log(f"Failed to read briefing file: {e}")
        print(f"브리핑 파일을 읽을 수 없습니다: {e}", file=sys.stderr)
        return 1

    channels = get_active_channels(config)
    if not channels:
        log("No active notification channels. Skipping.")
        return 0

    # 먼저 큐 플러시
    for ch in channels:
        flush_queue(ch, config)

    ok = True
    for ch in channels:
        payload = ch.build_briefing_payload(date, content)
        if send_with_retry(ch, payload, config):
            log(f"Briefing notification sent ({date}).", ch.name)
        else:
            enqueue("briefing", payload)
            log(f"Briefing notification failed. Queued.", ch.name)
            ok = False
    return 0 if ok else 1


def action_anomaly(config, anomalies_json):
    """이상 탐지 알림 전송."""
    try:
        anomalies = json.loads(anomalies_json)
    except (json.JSONDecodeError, TypeError):
        print("유효하지 않은 anomaly JSON", file=sys.stderr)
        return 2

    if not isinstance(anomalies, list):
        print("anomaly JSON은 배열이어야 합니다", file=sys.stderr)
        return 2

    if not anomalies:
        return 0

    channels = get_active_channels(config)
    if not channels:
        return 0

    ok = True
    for ch in channels:
        payload = ch.build_anomaly_payload(anomalies)
        if payload is None:
            continue
        if send_with_retry(ch, payload, config):
            log(f"Anomaly alert sent ({len(anomalies)} items).", ch.name)
        else:
            enqueue("anomaly", payload)
            log(f"Anomaly alert failed. Queued.", ch.name)
            ok = False
    return 0 if ok else 1


def action_flush(config):
    """큐 플러시."""
    channels = get_active_channels(config)
    if not channels:
        print("설정된 알림 채널이 없습니다.", file=sys.stderr)
        return 2

    total_sent = 0
    total_failed = 0
    for ch in channels:
        sent, failed = flush_queue(ch, config)
        total_sent += sent
        total_failed += failed

    print(f"플러시 완료: {total_sent}건 전송, {total_failed}건 실패")
    return 0 if total_failed == 0 else 1


def action_status(config):
    """채널 상태 출력."""
    statuses = get_channel_status(config)
    queue_info = statuses.pop("_queue", {})

    print("알림 채널 상태:")
    for key, info in statuses.items():
        state = "활성" if info["configured"] else "미설정"
        print(f"  [{key}] {state}")

    pending = queue_info.get("pending", 0)
    if pending > 0:
        print(f"\n대기 중인 메시지: {pending}건")
    else:
        print(f"\n대기 중인 메시지: 없음")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: send-notification.py <briefing|test|anomaly|flush|status> [args]", file=sys.stderr)
        return 2

    action = sys.argv[1]
    config = load_config()

    if action == "test":
        return action_test(config)
    elif action == "briefing":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        return action_briefing(config, date)
    elif action == "anomaly":
        anomalies_json = sys.argv[2] if len(sys.argv) > 2 else "[]"
        return action_anomaly(config, anomalies_json)
    elif action == "flush":
        return action_flush(config)
    elif action == "status":
        return action_status(config)
    else:
        print(f"알 수 없는 액션: {action}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
