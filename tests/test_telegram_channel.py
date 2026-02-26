"""tests/test_telegram_channel.py — TelegramChannel 클래스 테스트"""

import json
import os
import sys
import urllib.error
import urllib.request

import pytest

# conftest.py에서 단일 모듈 객체로 로드됨
import send_notification

from send_notification import (
    TelegramChannel,
    _extract_section,
    _truncate,
)


# ---------- fixtures ----------
# tmp_plugin_dir는 conftest.py에서 공유 fixture로 정의됨


@pytest.fixture
def telegram_config(tmp_plugin_dir):
    """Telegram bot_token + chat_id가 설정된 config를 생성."""
    config = {
        "notifications": {
            "telegram": {
                "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "chat_id": "987654321",
                "enabled": True,
            }
        }
    }
    (tmp_plugin_dir / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


# ---------- TelegramChannel.is_configured ----------


class TestTelegramIsConfigured:
    def test_name(self):
        assert TelegramChannel().name == "telegram"

    def test_configured_with_valid_token_and_chat_id(self, telegram_config):
        assert TelegramChannel().is_configured(telegram_config) is True

    def test_not_configured_no_token(self):
        config = {"notifications": {"telegram": {"bot_token": "", "chat_id": "123"}}}
        assert TelegramChannel().is_configured(config) is False

    def test_not_configured_no_chat_id(self):
        config = {"notifications": {"telegram": {"bot_token": "tok:en", "chat_id": ""}}}
        assert TelegramChannel().is_configured(config) is False

    def test_not_configured_disabled(self):
        config = {
            "notifications": {
                "telegram": {
                    "bot_token": "tok:en",
                    "chat_id": "123",
                    "enabled": False,
                }
            }
        }
        assert TelegramChannel().is_configured(config) is False

    def test_not_configured_empty_config(self):
        assert TelegramChannel().is_configured({}) is False

    def test_not_configured_missing_telegram_section(self):
        config = {"notifications": {"slack": {"webhook_url": "https://example.com"}}}
        assert TelegramChannel().is_configured(config) is False


# ---------- TelegramChannel.send ----------


class TestTelegramSend:
    def test_send_success(self, telegram_config, monkeypatch):
        class MockResp:
            status = 200
            def read(self):
                return json.dumps({"ok": True}).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        assert TelegramChannel().send({"text": "hi"}, telegram_config) is True

    def test_send_failure_url_error(self, telegram_config, monkeypatch):
        def raise_url_error(*a, **kw):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", raise_url_error)
        assert TelegramChannel().send({"text": "hi"}, telegram_config) is False

    def test_send_failure_api_returns_not_ok(self, telegram_config, monkeypatch):
        class MockResp:
            status = 200
            def read(self):
                return json.dumps({"ok": False, "description": "Bad Request"}).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        assert TelegramChannel().send({"text": "hi"}, telegram_config) is False

    def test_send_no_token(self):
        config = {"notifications": {"telegram": {"bot_token": "", "chat_id": "123"}}}
        assert TelegramChannel().send({"text": "hi"}, config) is False

    def test_send_no_chat_id(self):
        config = {"notifications": {"telegram": {"bot_token": "tok:en", "chat_id": ""}}}
        assert TelegramChannel().send({"text": "hi"}, config) is False

    def test_send_constructs_correct_url(self, telegram_config, monkeypatch):
        """bot_token이 URL에 올바르게 포함되는지 확인."""
        captured = {}

        class MockResp:
            status = 200
            def read(self):
                return json.dumps({"ok": True}).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        def capture_urlopen(req, **kw):
            captured["url"] = req.full_url
            captured["data"] = json.loads(req.data.decode("utf-8"))
            return MockResp()

        monkeypatch.setattr(urllib.request, "urlopen", capture_urlopen)
        TelegramChannel().send({"text": "hello"}, telegram_config)

        token = telegram_config["notifications"]["telegram"]["bot_token"]
        assert captured["url"] == f"https://api.telegram.org/bot{token}/sendMessage"
        assert captured["data"]["chat_id"] == "987654321"
        assert captured["data"]["text"] == "hello"


# ---------- TelegramChannel.build_test_payload ----------


class TestTelegramBuildTestPayload:
    def test_structure(self):
        payload = TelegramChannel().build_test_payload()
        assert "text" in payload
        assert "parse_mode" in payload
        assert payload["parse_mode"] == "HTML"

    def test_text_contains_setup_message(self):
        payload = TelegramChannel().build_test_payload()
        assert "정상적으로 설정" in payload["text"]


# ---------- TelegramChannel.build_briefing_payload ----------


class TestTelegramBuildBriefingPayload:
    def test_basic_structure(self):
        content = "## 핵심 요약\n요약 내용\n\n## 주요 지표\n지표 내용"
        payload = TelegramChannel().build_briefing_payload("2026-02-26", content)
        assert "text" in payload
        assert "parse_mode" in payload
        assert payload["parse_mode"] == "HTML"
        assert "GA 일일 브리핑 - 2026-02-26" in payload["text"]

    def test_contains_extracted_sections(self):
        content = "## 핵심 요약\n요약 내용입니다\n\n## 주요 지표\n지표 내용입니다"
        payload = TelegramChannel().build_briefing_payload("2026-02-26", content)
        assert "요약 내용입니다" in payload["text"]
        assert "지표 내용입니다" in payload["text"]
        assert "<b>핵심 요약</b>" in payload["text"]
        assert "<b>주요 지표</b>" in payload["text"]

    def test_empty_content(self):
        payload = TelegramChannel().build_briefing_payload("2026-02-26", "")
        assert "text" in payload
        # 헤더는 항상 포함
        assert "GA 일일 브리핑 - 2026-02-26" in payload["text"]

    def test_truncation_at_4096_chars(self):
        """Telegram 메시지 4096자 제한을 확인."""
        # 매우 긴 섹션 생성
        long_content = "## 핵심 요약\n" + "가" * 5000 + "\n\n## 주요 지표\n" + "나" * 5000
        payload = TelegramChannel().build_briefing_payload("2026-02-26", long_content)
        assert len(payload["text"]) <= 4096

    def test_truncation_ends_with_ellipsis(self):
        """4096자 초과 시 말줄임표로 끝나는지 확인."""
        long_content = "## 핵심 요약\n" + "가" * 5000 + "\n\n## 주요 지표\n" + "나" * 5000
        payload = TelegramChannel().build_briefing_payload("2026-02-26", long_content)
        assert payload["text"].endswith("...")

    def test_section_extraction_with_all_sections(self):
        content = (
            "## 핵심 요약\n요약\n\n"
            "## 주요 지표\n지표\n\n"
            "## 이상 탐지\n이상\n\n"
            "## 인사이트\n통찰\n\n"
            "## 액션 아이템\n행동"
        )
        payload = TelegramChannel().build_briefing_payload("2026-02-26", content)
        text = payload["text"]
        assert "<b>핵심 요약</b>" in text
        assert "<b>주요 지표</b>" in text
        assert "<b>이상 탐지</b>" in text
        assert "<b>인사이트</b>" in text
        assert "<b>액션 아이템</b>" in text


# ---------- TelegramChannel.build_anomaly_payload ----------


class TestTelegramBuildAnomalyPayload:
    def test_normal_anomalies(self):
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": -30.0, "severity": "critical"},
        ]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        assert "text" in payload
        assert "parse_mode" in payload
        assert payload["parse_mode"] == "HTML"
        text = payload["text"]
        assert "sessions" in text
        assert "+25.0%" in text
        assert "bounceRate" in text
        assert "-30.0%" in text

    def test_empty_anomalies_returns_none(self):
        assert TelegramChannel().build_anomaly_payload([]) is None

    def test_non_numeric_change_pct_none(self):
        anomalies = [{"metric": "sessions", "change_pct": None, "severity": "warning"}]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        assert "sessions" in payload["text"]
        assert "0.0%" in payload["text"]

    def test_non_numeric_change_pct_string(self):
        anomalies = [{"metric": "sessions", "change_pct": "bad", "severity": "warning"}]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        assert "0.0%" in payload["text"]

    def test_severity_icons(self):
        anomalies = [
            {"metric": "m1", "change_pct": 10.0, "severity": "critical"},
            {"metric": "m2", "change_pct": 5.0, "severity": "warning"},
        ]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        text = payload["text"]
        # critical -> U+1F6A8, warning -> U+26A0 + FE0F
        assert "\U0001f6a8" in text
        assert "\u26a0\ufe0f" in text

    def test_positive_direction_prefix(self):
        anomalies = [{"metric": "sessions", "change_pct": 15.0, "severity": "warning"}]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert "+15.0%" in payload["text"]

    def test_negative_direction_no_prefix(self):
        anomalies = [{"metric": "sessions", "change_pct": -10.0, "severity": "warning"}]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert "-10.0%" in payload["text"]
        # + 기호가 없어야 함
        assert "+-10.0%" not in payload["text"]

    def test_header_text(self):
        anomalies = [{"metric": "sessions", "change_pct": 5.0, "severity": "warning"}]
        payload = TelegramChannel().build_anomaly_payload(anomalies)
        assert "<b>이상 탐지 알림</b>" in payload["text"]
