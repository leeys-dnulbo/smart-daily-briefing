"""tests/test_send_notification.py — scripts/send-notification.py 테스트"""

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request

import pytest

# 파일명에 하이픈이 있어서 importlib로 로드
_spec = importlib.util.spec_from_file_location(
    "send_notification",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "send-notification.py"),
)
send_notification = importlib.util.module_from_spec(_spec)
sys.modules["send_notification"] = send_notification
_spec.loader.exec_module(send_notification)

from send_notification import (
    CHANNELS,
    MAX_FLUSH_RETRIES,
    SlackChannel,
    NotificationChannel,
    _extract_section,
    _truncate,
    enqueue,
    flush_queue,
    get_active_channels,
    get_channel_status,
    load_config,
    log,
    main,
    send_with_retry,
    action_test,
    action_briefing,
    action_anomaly,
    action_flush,
    action_status,
)


# ---------- fixtures ----------


@pytest.fixture
def tmp_plugin_dir(tmp_path, monkeypatch):
    """임시 플러그인 디렉토리를 생성하고 모듈 전역 변수를 패치."""
    briefings_dir = tmp_path / "briefings"
    briefings_dir.mkdir()
    config_path = tmp_path / "config.json"

    import send_notification as mod

    monkeypatch.setattr(mod, "PLUGIN_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(mod, "QUEUE_PATH", str(briefings_dir / "notification-queue.json"))
    monkeypatch.setattr(mod, "LOG_PATH", str(briefings_dir / "schedule.log"))
    return tmp_path


@pytest.fixture
def slack_config(tmp_plugin_dir):
    """Slack webhook이 설정된 config를 생성."""
    config = {
        "notifications": {
            "slack": {
                "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
                "enabled": True,
            }
        }
    }
    (tmp_plugin_dir / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


# ---------- NotificationChannel 인터페이스 ----------


class TestNotificationChannel:
    def test_base_class_not_implemented(self):
        ch = NotificationChannel()
        with pytest.raises(NotImplementedError):
            ch.is_configured({})
        with pytest.raises(NotImplementedError):
            ch.send({}, {})
        with pytest.raises(NotImplementedError):
            ch.build_test_payload()
        with pytest.raises(NotImplementedError):
            ch.build_briefing_payload("2026-02-26", "")
        with pytest.raises(NotImplementedError):
            ch.build_anomaly_payload([])


# ---------- SlackChannel ----------


class TestSlackChannel:
    def test_name(self):
        assert SlackChannel().name == "slack"

    def test_is_configured_with_valid_url(self, slack_config):
        assert SlackChannel().is_configured(slack_config) is True

    def test_is_configured_no_url(self):
        config = {"notifications": {"slack": {"webhook_url": ""}}}
        assert SlackChannel().is_configured(config) is False

    def test_is_configured_disabled(self):
        config = {
            "notifications": {
                "slack": {
                    "webhook_url": "https://hooks.slack.com/test",
                    "enabled": False,
                }
            }
        }
        assert SlackChannel().is_configured(config) is False

    def test_is_configured_http_not_https(self):
        config = {
            "notifications": {
                "slack": {"webhook_url": "http://hooks.slack.com/test"}
            }
        }
        assert SlackChannel().is_configured(config) is False

    def test_is_configured_empty_config(self):
        assert SlackChannel().is_configured({}) is False

    def test_send_success(self, slack_config, monkeypatch):
        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        assert SlackChannel().send({"text": "hi"}, slack_config) is True

    def test_send_failure_http_error(self, slack_config, monkeypatch):
        def raise_url_error(*a, **kw):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", raise_url_error)
        assert SlackChannel().send({"text": "hi"}, slack_config) is False

    def test_send_no_url(self):
        config = {"notifications": {"slack": {"webhook_url": ""}}}
        assert SlackChannel().send({"text": "hi"}, config) is False

    def test_build_test_payload(self):
        payload = SlackChannel().build_test_payload()
        assert "blocks" in payload
        assert len(payload["blocks"]) == 1
        assert "정상적으로 설정" in payload["blocks"][0]["text"]["text"]

    def test_build_briefing_payload_basic(self):
        content = "## 핵심 요약\n요약 내용\n\n## 주요 지표\n지표 내용"
        payload = SlackChannel().build_briefing_payload("2026-02-26", content)
        assert "blocks" in payload
        # header + divider + section(핵심 요약) + divider + section(주요 지표)
        assert len(payload["blocks"]) >= 3

    def test_build_briefing_payload_with_meta(self):
        content = "## 핵심 요약\n내용\n\n> 프리셋: default | 조회 기간: 7일"
        payload = SlackChannel().build_briefing_payload("2026-02-26", content)
        # context block이 포함되어야 함
        types = [b["type"] for b in payload["blocks"]]
        assert "context" in types

    def test_build_briefing_payload_empty(self):
        payload = SlackChannel().build_briefing_payload("2026-02-26", "")
        assert "blocks" in payload
        # header만 있어야 함
        assert payload["blocks"][0]["type"] == "header"

    def test_build_anomaly_payload(self):
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": -30.0, "severity": "critical"},
        ]
        payload = SlackChannel().build_anomaly_payload(anomalies)
        assert payload is not None
        text = payload["blocks"][0]["text"]["text"]
        assert "sessions" in text
        assert "+25.0%" in text
        assert "bounceRate" in text
        assert "-30.0%" in text

    def test_build_anomaly_payload_empty(self):
        assert SlackChannel().build_anomaly_payload([]) is None


# ---------- 유틸리티 ----------


class TestUtilities:
    def test_extract_section_basic(self):
        md = "## 핵심 요약\n내용1\n\n## 주요 지표\n내용2"
        assert _extract_section(md, "핵심 요약") == "내용1"
        assert _extract_section(md, "주요 지표") == "내용2"

    def test_extract_section_not_found(self):
        assert _extract_section("## Other\ncontent", "핵심 요약") == ""

    def test_truncate_short(self):
        assert _truncate("hello") == "hello"

    def test_truncate_long(self):
        long_text = "x" * 3000
        result = _truncate(long_text)
        assert len(result) < 3000
        assert result.endswith("...")


# ---------- load_config ----------


class TestLoadConfig:
    def test_no_config_file(self, tmp_plugin_dir):
        assert load_config() == {}

    def test_valid_config(self, tmp_plugin_dir, slack_config):
        config = load_config()
        assert "notifications" in config

    def test_invalid_json(self, tmp_plugin_dir):
        (tmp_plugin_dir / "config.json").write_text("{bad", encoding="utf-8")
        assert load_config() == {}


# ---------- send_with_retry ----------


class TestSendWithRetry:
    def test_success_first_try(self, slack_config, monkeypatch):
        ch = SlackChannel()

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        assert send_with_retry(ch, {"text": "hi"}, slack_config) is True

    def test_all_retries_fail(self, slack_config, monkeypatch):
        ch = SlackChannel()

        def raise_error(*a, **kw):
            raise urllib.error.URLError("fail")

        monkeypatch.setattr(urllib.request, "urlopen", raise_error)
        # max_retries=1 to keep test fast
        assert send_with_retry(ch, {"text": "hi"}, slack_config, max_retries=1) is False

    def test_retry_then_success(self, slack_config, monkeypatch):
        ch = SlackChannel()
        call_count = {"n": 0}

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def flaky_urlopen(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise urllib.error.URLError("transient")
            return MockResp()

        monkeypatch.setattr(urllib.request, "urlopen", flaky_urlopen)
        # patch time.sleep to avoid waiting
        import send_notification as mod
        monkeypatch.setattr(mod.time, "sleep", lambda s: None)
        assert send_with_retry(ch, {"text": "hi"}, slack_config, max_retries=3) is True


# ---------- enqueue / flush_queue ----------


class TestQueue:
    def test_enqueue_creates_file(self, tmp_plugin_dir):
        enqueue("test", {"text": "hello"})
        import send_notification as mod
        assert os.path.exists(mod.QUEUE_PATH)
        with open(mod.QUEUE_PATH, encoding="utf-8") as f:
            queue = json.load(f)
        assert len(queue) == 1
        assert queue[0]["type"] == "test"

    def test_enqueue_appends(self, tmp_plugin_dir):
        enqueue("test", {"text": "1"})
        enqueue("test", {"text": "2"})
        import send_notification as mod
        with open(mod.QUEUE_PATH, encoding="utf-8") as f:
            queue = json.load(f)
        assert len(queue) == 2

    def test_enqueue_respects_max_size(self, tmp_plugin_dir, monkeypatch):
        import send_notification as mod
        monkeypatch.setattr(mod, "MAX_QUEUE_SIZE", 3)
        for i in range(5):
            enqueue("test", {"n": i})
        with open(mod.QUEUE_PATH, encoding="utf-8") as f:
            queue = json.load(f)
        assert len(queue) == 3
        # 가장 오래된 것이 제거됨
        assert queue[0]["payload"]["n"] == 2

    def test_flush_empty_queue(self, tmp_plugin_dir, slack_config):
        ch = SlackChannel()
        sent, failed = flush_queue(ch, slack_config)
        assert sent == 0
        assert failed == 0

    def test_flush_sends_queued_messages(self, tmp_plugin_dir, slack_config, monkeypatch):
        enqueue("test", {"text": "queued"})

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        ch = SlackChannel()
        sent, failed = flush_queue(ch, slack_config)
        assert sent == 1
        assert failed == 0

    def test_flush_keeps_failed(self, tmp_plugin_dir, slack_config, monkeypatch):
        enqueue("test", {"text": "will fail"})

        def raise_error(*a, **kw):
            raise urllib.error.URLError("fail")

        monkeypatch.setattr(urllib.request, "urlopen", raise_error)
        ch = SlackChannel()
        sent, failed = flush_queue(ch, slack_config)
        assert sent == 0
        assert failed == 1
        # 큐 파일에 여전히 남아있어야 함
        import send_notification as mod
        with open(mod.QUEUE_PATH, encoding="utf-8") as f:
            queue = json.load(f)
        assert len(queue) == 1
        assert queue[0]["retries"] == 1


# ---------- get_active_channels / get_channel_status ----------


class TestChannelRouting:
    def test_no_active_channels_empty_config(self):
        assert get_active_channels({}) == []

    def test_active_channels_with_slack(self, slack_config):
        channels = get_active_channels(slack_config)
        assert len(channels) == 1
        assert channels[0].name == "slack"

    def test_channel_status_configured(self, tmp_plugin_dir, slack_config):
        config = load_config()
        statuses = get_channel_status(config)
        assert "slack" in statuses
        assert statuses["slack"]["configured"] is True
        assert "_queue" in statuses

    def test_channel_status_not_configured(self, tmp_plugin_dir):
        statuses = get_channel_status({})
        assert statuses["slack"]["configured"] is False

    def test_channel_status_queue_count(self, tmp_plugin_dir):
        enqueue("test", {"text": "q"})
        config = load_config()
        statuses = get_channel_status(config)
        assert statuses["_queue"]["pending"] == 1


# ---------- CLI actions ----------


class TestActionTest:
    def test_no_channels(self, tmp_plugin_dir, capsys):
        result = action_test({})
        assert result == 2
        captured = capsys.readouterr()
        assert "설정된 알림 채널이 없습니다" in captured.err

    def test_success(self, tmp_plugin_dir, slack_config, monkeypatch, capsys):
        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        result = action_test(slack_config)
        assert result == 0
        captured = capsys.readouterr()
        assert "전송 성공" in captured.out

    def test_failure(self, tmp_plugin_dir, slack_config, monkeypatch, capsys):
        def raise_error(*a, **kw):
            raise urllib.error.URLError("fail")

        monkeypatch.setattr(urllib.request, "urlopen", raise_error)
        import send_notification as mod
        monkeypatch.setattr(mod.time, "sleep", lambda s: None)
        result = action_test(slack_config)
        assert result == 1
        captured = capsys.readouterr()
        assert "전송 실패" in captured.err


class TestActionBriefing:
    def test_no_briefing_file(self, tmp_plugin_dir, slack_config, capsys):
        result = action_briefing(slack_config, "2026-02-26")
        assert result == 1
        captured = capsys.readouterr()
        assert "찾을 수 없습니다" in captured.err

    def test_no_channels_returns_ok(self, tmp_plugin_dir):
        briefings_dir = tmp_plugin_dir / "briefings"
        (briefings_dir / "2026-02-26.md").write_text("## 핵심 요약\n내용", encoding="utf-8")
        result = action_briefing({}, "2026-02-26")
        assert result == 0  # 채널 없으면 skip

    def test_send_success(self, tmp_plugin_dir, slack_config, monkeypatch):
        briefings_dir = tmp_plugin_dir / "briefings"
        (briefings_dir / "2026-02-26.md").write_text(
            "## 핵심 요약\n내용\n\n## 주요 지표\n지표", encoding="utf-8"
        )

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        result = action_briefing(slack_config, "2026-02-26")
        assert result == 0

    def test_send_failure_queues(self, tmp_plugin_dir, slack_config, monkeypatch):
        briefings_dir = tmp_plugin_dir / "briefings"
        (briefings_dir / "2026-02-26.md").write_text("## 핵심 요약\n내용", encoding="utf-8")

        def raise_error(*a, **kw):
            raise urllib.error.URLError("fail")

        monkeypatch.setattr(urllib.request, "urlopen", raise_error)
        import send_notification as mod
        monkeypatch.setattr(mod.time, "sleep", lambda s: None)
        result = action_briefing(slack_config, "2026-02-26")
        assert result == 1
        # 큐에 저장되었는지 확인
        assert os.path.exists(mod.QUEUE_PATH)


class TestActionAnomaly:
    def test_invalid_json(self, tmp_plugin_dir, capsys):
        result = action_anomaly({}, "not-json")
        assert result == 2

    def test_empty_anomalies(self, tmp_plugin_dir):
        result = action_anomaly({}, "[]")
        assert result == 0

    def test_no_channels(self, tmp_plugin_dir):
        result = action_anomaly({}, '[{"metric":"sessions","change_pct":25,"severity":"warning"}]')
        assert result == 0

    def test_send_success(self, tmp_plugin_dir, slack_config, monkeypatch):
        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        anomalies = '[{"metric":"sessions","change_pct":25,"severity":"warning"}]'
        result = action_anomaly(slack_config, anomalies)
        assert result == 0


class TestActionFlush:
    def test_no_channels(self, tmp_plugin_dir, capsys):
        result = action_flush({})
        assert result == 2

    def test_empty_queue(self, tmp_plugin_dir, slack_config, capsys):
        result = action_flush(slack_config)
        assert result == 0
        captured = capsys.readouterr()
        assert "0건 전송" in captured.out

    def test_flush_with_messages(self, tmp_plugin_dir, slack_config, monkeypatch, capsys):
        enqueue("test", {"text": "queued"})

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        result = action_flush(slack_config)
        assert result == 0
        captured = capsys.readouterr()
        assert "1건 전송" in captured.out


class TestActionStatus:
    def test_output(self, tmp_plugin_dir, capsys):
        result = action_status({})
        assert result == 0
        captured = capsys.readouterr()
        assert "알림 채널 상태" in captured.out
        assert "slack" in captured.out
        assert "미설정" in captured.out

    def test_with_queue(self, tmp_plugin_dir, capsys):
        enqueue("test", {"text": "q"})
        result = action_status({})
        assert result == 0
        captured = capsys.readouterr()
        assert "1건" in captured.out


# ---------- log ----------


class TestLog:
    def test_log_writes_to_file(self, tmp_plugin_dir):
        log("test message")
        import send_notification as mod
        assert os.path.exists(mod.LOG_PATH)
        with open(mod.LOG_PATH, encoding="utf-8") as f:
            content = f.read()
        assert "test message" in content
        assert "[notify]" in content

    def test_log_custom_channel(self, tmp_plugin_dir):
        log("slack msg", "slack")
        import send_notification as mod
        with open(mod.LOG_PATH, encoding="utf-8") as f:
            content = f.read()
        assert "[slack]" in content


# ---------- flush max retries ----------


class TestFlushMaxRetries:
    def test_drops_after_max_retries(self, tmp_plugin_dir, slack_config, monkeypatch):
        import send_notification as mod

        # 직접 큐 파일에 MAX_FLUSH_RETRIES 이상인 항목 작성
        queue = [{"type": "test", "payload": {"text": "old"}, "retries": MAX_FLUSH_RETRIES + 1}]
        queue_path = mod.QUEUE_PATH
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        ch = SlackChannel()
        sent, failed = flush_queue(ch, slack_config)
        assert sent == 0
        assert failed == 0  # dropped, not failed

        # 큐 파일이 비어있어야 함
        with open(queue_path, encoding="utf-8") as f:
            remaining = json.load(f)
        assert len(remaining) == 0


# ---------- main() ----------


class TestMain:
    def test_no_args(self, tmp_plugin_dir, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["send-notification.py"])
        result = main()
        assert result == 2
        captured = capsys.readouterr()
        assert "Usage" in captured.err

    def test_unknown_action(self, tmp_plugin_dir, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["send-notification.py", "unknown"])
        result = main()
        assert result == 2
        captured = capsys.readouterr()
        assert "알 수 없는 액션" in captured.err

    def test_dispatches_status(self, tmp_plugin_dir, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["send-notification.py", "status"])
        result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "알림 채널 상태" in captured.out

    def test_dispatches_test(self, tmp_plugin_dir, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["send-notification.py", "test"])
        result = main()
        assert result == 2  # no channels configured


# ---------- extract_section edge cases ----------


class TestExtractSectionEdgeCases:
    def test_crlf_line_endings(self):
        md = "## 핵심 요약\r\n내용1\r\n\r\n## 주요 지표\r\n내용2"
        assert _extract_section(md, "핵심 요약") == "내용1"

    def test_trailing_whitespace_in_heading(self):
        md = "## 핵심 요약   \n내용1\n\n## 주요 지표\n내용2"
        assert _extract_section(md, "핵심 요약") == "내용1"

    def test_last_section_no_trailing_heading(self):
        md = "## 액션 아이템\n- item 1\n- item 2"
        assert _extract_section(md, "액션 아이템") == "- item 1\n- item 2"


# ---------- date validation ----------


class TestDateValidation:
    def test_briefing_path_traversal(self, tmp_plugin_dir, slack_config, capsys):
        result = action_briefing(slack_config, "../../etc/passwd")
        assert result == 2
        captured = capsys.readouterr()
        assert "유효하지 않은 날짜" in captured.err

    def test_briefing_valid_date_format(self, tmp_plugin_dir, slack_config, capsys):
        result = action_briefing(slack_config, "2026-02-26")
        # 파일이 없으므로 1을 반환하지만, 날짜 검증은 통과
        assert result == 1


# ---------- anomaly JSON type validation ----------


class TestAnomalyJsonType:
    def test_dict_json_rejected(self, tmp_plugin_dir, capsys):
        result = action_anomaly({}, '{"metric":"sessions"}')
        assert result == 2
        captured = capsys.readouterr()
        assert "배열" in captured.err

    def test_string_json_rejected(self, tmp_plugin_dir, capsys):
        result = action_anomaly({}, '"just a string"')
        assert result == 2
        captured = capsys.readouterr()
        assert "배열" in captured.err

    def test_number_json_rejected(self, tmp_plugin_dir, capsys):
        result = action_anomaly({}, '42')
        assert result == 2
