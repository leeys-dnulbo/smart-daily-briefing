#!/usr/bin/env python3
"""
Smart Daily Briefing - Python 통합 알림 시스템

v1.12.0에서 도입. v2.0.0에서 멀티채널(Slack/Telegram/Discord) 지원.
v2.0.0에서 Telegram/Discord 멀티채널 지원 추가.
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


# 브리핑 섹션 목록 (heading, label) — 3채널 공통
BRIEFING_SECTIONS = [
    ("핵심 요약", "핵심 요약"),
    ("주요 지표", "주요 지표"),
    ("이상 탐지", "이상 탐지"),
    ("인사이트", "인사이트"),
    ("액션 아이템", "액션 아이템"),
]


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

        for heading, label in BRIEFING_SECTIONS:
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
            if not isinstance(a, dict):
                continue
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
        text = "\n".join(lines)
        # Slack section block mrkdwn 3000자 제한
        if len(text) > 3000:
            text = text[:2996] + "\n..."
        return {
            "blocks": [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }]
        }


class TelegramChannel(NotificationChannel):
    """Telegram Bot API 채널. bot_token + chat_id 기반."""
    name = "telegram"

    def is_configured(self, config):
        tg = config.get("notifications", {}).get("telegram", {})
        return (
            bool(tg.get("bot_token"))
            and bool(tg.get("chat_id"))
            and tg.get("enabled", True)
        )

    def send(self, payload, config):
        tg = config.get("notifications", {}).get("telegram", {})
        token = tg.get("bot_token", "")
        chat_id = tg.get("chat_id", "")
        if not token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        send_payload = {**payload, "chat_id": chat_id}
        data = json.dumps(send_payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return False

    def build_test_payload(self):
        return {
            "text": "Smart Daily Briefing 알림이 정상적으로 설정되었습니다.",
            "parse_mode": "HTML",
        }

    def build_briefing_payload(self, date, content):
        parts = [f"<b>GA 일일 브리핑 - {date}</b>"]
        for heading, label in BRIEFING_SECTIONS:
            text = _extract_section(content, heading)
            if text:
                # HTML 특수문자 이스케이프
                safe_text = _html_escape(text)
                parts.append(f"\n<b>{label}</b>\n{_truncate(safe_text, 800)}")

        msg = "\n".join(parts)
        # Telegram 메시지 4096자 제한 — HTML 태그/엔티티 중간 절단 방지
        if len(msg) > 4096:
            cut = msg[:4090]
            # 열린 HTML 엔티티(&amp; 등) 절단 방지
            amp_pos = cut.rfind("&")
            if amp_pos != -1 and ";" not in cut[amp_pos:]:
                cut = cut[:amp_pos]
            # 열린 HTML 태그 절단 방지
            lt_pos = cut.rfind("<")
            if lt_pos != -1 and ">" not in cut[lt_pos:]:
                cut = cut[:lt_pos]
            msg = cut + "\n..."
        return {"text": msg, "parse_mode": "HTML"}

    def build_anomaly_payload(self, anomalies):
        if not anomalies:
            return None
        lines = ["<b>이상 탐지 알림</b>", ""]
        for a in anomalies:
            if not isinstance(a, dict):
                continue
            metric = _html_escape(str(a.get("metric", "?")))
            change = a.get("change_pct", 0)
            try:
                change = float(change)
            except (TypeError, ValueError):
                change = 0.0
            severity = _html_escape(str(a.get("severity", "warning")))
            icon = "\U0001f6a8" if severity == "critical" else "\u26a0\ufe0f"
            direction = "+" if change > 0 else ""
            lines.append(f"{icon} <b>{metric}</b>: {direction}{change:.1f}% ({severity})")
        msg = "\n".join(lines)
        if len(msg) > 4096:
            msg = msg[:4090] + "\n..."
        return {"text": msg, "parse_mode": "HTML"}


class DiscordChannel(NotificationChannel):
    """Discord Webhook 채널. embed 형식 사용."""
    name = "discord"

    def is_configured(self, config):
        dc = config.get("notifications", {}).get("discord", {})
        url = dc.get("webhook_url", "")
        return bool(url) and url.startswith("https://") and dc.get("enabled", True)

    def send(self, payload, config):
        url = config.get("notifications", {}).get("discord", {}).get("webhook_url", "")
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
                # Discord webhook 성공 시 200 또는 204 반환
                return resp.status in (200, 204)
        except (urllib.error.URLError, OSError):
            return False

    def build_test_payload(self):
        return {
            "embeds": [{
                "title": "Smart Daily Briefing",
                "description": "알림이 정상적으로 설정되었습니다.",
                "color": 0x2ECC71,
            }]
        }

    def build_briefing_payload(self, date, content):
        fields = []
        for heading, label in BRIEFING_SECTIONS:
            text = _extract_section(content, heading)
            if text:
                fields.append({
                    "name": label,
                    "value": _truncate(text, 1024),
                    "inline": False,
                })
        return {
            "embeds": [{
                "title": f"GA 일일 브리핑 - {date}",
                "color": 0x3498DB,
                "fields": fields,
            }]
        }

    def build_anomaly_payload(self, anomalies):
        if not anomalies:
            return None
        lines = []
        for a in anomalies:
            if not isinstance(a, dict):
                continue
            metric = a.get("metric", "?")
            change = a.get("change_pct", 0)
            try:
                change = float(change)
            except (TypeError, ValueError):
                change = 0.0
            severity = a.get("severity", "warning")
            icon = "\U0001f6a8" if severity == "critical" else "\u26a0\ufe0f"
            direction = "+" if change > 0 else ""
            lines.append(f"{icon} **{metric}**: {direction}{change:.1f}% ({severity})")
        desc = "\n".join(lines)
        # Discord embed description 4096자 제한
        if len(desc) > 4096:
            desc = desc[:4092] + "\n..."
        return {
            "embeds": [{
                "title": "이상 탐지 알림",
                "description": desc,
                "color": 0xE74C3C,
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
    suffix = "\n..."
    if len(text) > limit:
        return text[:limit - len(suffix)] + suffix
    return text


def _html_escape(text):
    """Telegram HTML 파싱에 필요한 최소 이스케이프."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def enqueue(msg_type, payload, channel_name="all"):
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
        "channel": channel_name,
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


def flush_queue(config):
    """큐에 쌓인 메시지를 재전송. 채널별로 라우팅."""
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
            log(f"Dropping message after {retries} retries (type={entry.get('type', '?')})")
            continue

        payload = entry.get("payload", {})
        # v1.12 큐 호환: channel 필드 없으면 "slack" 기본값
        channel_name = entry.get("channel", "slack")

        # 대상 채널 결정
        if channel_name == "all":
            targets = get_active_channels(config)
        elif channel_name in CHANNELS:
            ch = CHANNELS[channel_name]
            targets = [ch] if ch.is_configured(config) else []
        else:
            log(f"Unknown channel in queue: {channel_name}, dropping")
            continue

        entry_sent = False
        for ch in targets:
            if ch.send(payload, config):
                entry_sent = True
                log(f"Flushed queued message (type={entry.get('type', '?')})", ch.name)

        if entry_sent:
            sent += 1
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
        log(f"Failed to update queue file after flush: {e}")
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

# 채널 레지스트리
CHANNELS = {
    "slack": SlackChannel(),
    "telegram": TelegramChannel(),
    "discord": DiscordChannel(),
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
                data = json.load(f)
                queue_size = len(data) if isinstance(data, list) else 0
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    statuses["_queue"] = {"pending": queue_size}
    return statuses


# ---------------------------------------------------------------------------
# CLI 액션
# ---------------------------------------------------------------------------

def action_test(config, target_channel=None):
    """테스트 메시지 전송. target_channel이 지정되면 해당 채널만 테스트."""
    if target_channel:
        if target_channel not in CHANNELS:
            print(f"알 수 없는 채널: {target_channel} (사용 가능: {', '.join(CHANNELS.keys())})", file=sys.stderr)
            return 2
        ch = CHANNELS[target_channel]
        if not ch.is_configured(config):
            print(f"[{target_channel}] 채널이 설정되지 않았습니다.", file=sys.stderr)
            return 2
        channels = [ch]
    else:
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
    flush_queue(config)

    ok = True
    for ch in channels:
        payload = ch.build_briefing_payload(date, content)
        if send_with_retry(ch, payload, config):
            log(f"Briefing notification sent ({date}).", ch.name)
        else:
            enqueue("briefing", payload, ch.name)
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
            enqueue("anomaly", payload, ch.name)
            log(f"Anomaly alert failed. Queued.", ch.name)
            ok = False
    return 0 if ok else 1


def action_flush(config):
    """큐 플러시."""
    channels = get_active_channels(config)
    if not channels:
        print("설정된 알림 채널이 없습니다.", file=sys.stderr)
        return 2

    sent, failed = flush_queue(config)
    print(f"플러시 완료: {sent}건 전송, {failed}건 실패")
    return 0 if failed == 0 else 1


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
        target = sys.argv[2] if len(sys.argv) > 2 else None
        return action_test(config, target)
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
