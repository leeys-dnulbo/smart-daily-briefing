"""tests/test_discord_channel.py — DiscordChannel 테스트"""

import json
import os
import sys
import urllib.error
import urllib.request

import pytest

# conftest.py에서 단일 모듈 객체로 로드됨
import send_notification

from send_notification import DiscordChannel, _extract_section, _truncate


# ---------- fixtures ----------
# tmp_plugin_dir는 conftest.py에서 공유 fixture로 정의됨


@pytest.fixture
def discord_config(tmp_plugin_dir):
    """Discord webhook이 설정된 config를 생성."""
    config = {
        "notifications": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/123/abc",
                "enabled": True,
            }
        }
    }
    (tmp_plugin_dir / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


# ---------- DiscordChannel.is_configured ----------


class TestDiscordIsConfigured:
    def test_is_configured_with_valid_url(self, discord_config):
        assert DiscordChannel().is_configured(discord_config) is True

    def test_is_configured_no_url(self):
        config = {"notifications": {"discord": {"webhook_url": ""}}}
        assert DiscordChannel().is_configured(config) is False

    def test_is_configured_http_not_https(self):
        config = {
            "notifications": {
                "discord": {"webhook_url": "http://discord.com/api/webhooks/123/abc"}
            }
        }
        assert DiscordChannel().is_configured(config) is False

    def test_is_configured_disabled(self):
        config = {
            "notifications": {
                "discord": {
                    "webhook_url": "https://discord.com/api/webhooks/123/abc",
                    "enabled": False,
                }
            }
        }
        assert DiscordChannel().is_configured(config) is False

    def test_is_configured_empty_config(self):
        assert DiscordChannel().is_configured({}) is False


# ---------- DiscordChannel.send ----------


class TestDiscordSend:
    def test_send_success_204(self, discord_config, monkeypatch):
        class MockResp:
            status = 204
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        result = DiscordChannel().send({"embeds": []}, discord_config)
        assert result is True

    def test_send_success_200(self, discord_config, monkeypatch):
        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        result = DiscordChannel().send({"embeds": []}, discord_config)
        assert result is True

    def test_send_failure_url_error(self, discord_config, monkeypatch):
        def raise_url_error(*a, **kw):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", raise_url_error)
        result = DiscordChannel().send({"embeds": []}, discord_config)
        assert result is False

    def test_send_no_url(self):
        config = {"notifications": {"discord": {"webhook_url": ""}}}
        result = DiscordChannel().send({"embeds": []}, config)
        assert result is False


# ---------- DiscordChannel.build_test_payload ----------


class TestDiscordBuildTestPayload:
    def test_build_test_payload_structure(self):
        payload = DiscordChannel().build_test_payload()
        assert "embeds" in payload
        assert isinstance(payload["embeds"], list)
        assert len(payload["embeds"]) == 1

    def test_build_test_payload_color(self):
        payload = DiscordChannel().build_test_payload()
        embed = payload["embeds"][0]
        assert "color" in embed
        assert embed["color"] == 0x2ECC71

    def test_build_test_payload_content(self):
        payload = DiscordChannel().build_test_payload()
        embed = payload["embeds"][0]
        assert embed["title"] == "Smart Daily Briefing"
        assert "정상적으로 설정" in embed["description"]


# ---------- DiscordChannel.build_briefing_payload ----------


class TestDiscordBuildBriefingPayload:
    def test_embed_structure_with_fields(self):
        content = "## 핵심 요약\n요약 내용\n\n## 주요 지표\n지표 내용"
        payload = DiscordChannel().build_briefing_payload("2026-02-26", content)
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert embed["title"] == "GA 일일 브리핑 - 2026-02-26"
        assert embed["color"] == 0x3498DB
        assert "fields" in embed
        assert len(embed["fields"]) == 2

    def test_section_extraction(self):
        content = "## 핵심 요약\n요약 내용\n\n## 주요 지표\n지표 내용\n\n## 인사이트\n인사이트 내용"
        payload = DiscordChannel().build_briefing_payload("2026-02-26", content)
        fields = payload["embeds"][0]["fields"]
        names = [f["name"] for f in fields]
        assert "핵심 요약" in names
        assert "주요 지표" in names
        assert "인사이트" in names

    def test_field_inline_false(self):
        content = "## 핵심 요약\n요약 내용"
        payload = DiscordChannel().build_briefing_payload("2026-02-26", content)
        for field in payload["embeds"][0]["fields"]:
            assert field["inline"] is False

    def test_field_value_truncation_1024(self):
        long_text = "x" * 2000
        content = f"## 핵심 요약\n{long_text}"
        payload = DiscordChannel().build_briefing_payload("2026-02-26", content)
        field_value = payload["embeds"][0]["fields"][0]["value"]
        assert len(field_value) <= 1024
        assert field_value.endswith("...")

    def test_empty_content(self):
        payload = DiscordChannel().build_briefing_payload("2026-02-26", "")
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert embed["fields"] == []

    def test_all_five_sections(self):
        content = (
            "## 핵심 요약\n내용1\n\n"
            "## 주요 지표\n내용2\n\n"
            "## 이상 탐지\n내용3\n\n"
            "## 인사이트\n내용4\n\n"
            "## 액션 아이템\n내용5"
        )
        payload = DiscordChannel().build_briefing_payload("2026-02-26", content)
        fields = payload["embeds"][0]["fields"]
        assert len(fields) == 5
        expected_names = ["핵심 요약", "주요 지표", "이상 탐지", "인사이트", "액션 아이템"]
        actual_names = [f["name"] for f in fields]
        assert actual_names == expected_names


# ---------- DiscordChannel.build_anomaly_payload ----------


class TestDiscordBuildAnomalyPayload:
    def test_normal_anomalies_embed_format(self):
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": -30.0, "severity": "critical"},
        ]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert embed["title"] == "이상 탐지 알림"
        assert embed["color"] == 0xE74C3C
        desc = embed["description"]
        assert "sessions" in desc
        assert "+25.0%" in desc
        assert "bounceRate" in desc
        assert "-30.0%" in desc

    def test_empty_list_returns_none(self):
        assert DiscordChannel().build_anomaly_payload([]) is None

    def test_non_numeric_change_pct_none(self):
        anomalies = [{"metric": "sessions", "change_pct": None, "severity": "warning"}]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        desc = payload["embeds"][0]["description"]
        assert "sessions" in desc
        assert "0.0%" in desc

    def test_non_numeric_change_pct_string(self):
        anomalies = [{"metric": "sessions", "change_pct": "bad", "severity": "warning"}]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        desc = payload["embeds"][0]["description"]
        assert "0.0%" in desc

    def test_critical_and_warning_icons(self):
        anomalies = [
            {"metric": "a", "change_pct": 10, "severity": "critical"},
            {"metric": "b", "change_pct": -5, "severity": "warning"},
        ]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        desc = payload["embeds"][0]["description"]
        # critical 아이콘: U+1F6A8, warning 아이콘: U+26A0 + FE0F
        assert "\U0001f6a8" in desc
        assert "\u26a0\ufe0f" in desc

    def test_positive_direction_prefix(self):
        anomalies = [{"metric": "users", "change_pct": 15.0, "severity": "warning"}]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        desc = payload["embeds"][0]["description"]
        assert "+15.0%" in desc

    def test_negative_no_plus_prefix(self):
        anomalies = [{"metric": "users", "change_pct": -10.0, "severity": "warning"}]
        payload = DiscordChannel().build_anomaly_payload(anomalies)
        desc = payload["embeds"][0]["description"]
        assert "-10.0%" in desc
        assert "+-" not in desc
