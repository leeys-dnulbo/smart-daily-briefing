"""tests/test_anomaly_monitor.py — scripts/anomaly-monitor.py 테스트"""

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

import pytest

# 파일명에 하이픈이 있어서 importlib로 로드
_spec = importlib.util.spec_from_file_location(
    "anomaly_monitor",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "anomaly-monitor.py"),
)
anomaly_monitor = importlib.util.module_from_spec(_spec)
sys.modules["anomaly_monitor"] = anomaly_monitor
_spec.loader.exec_module(anomaly_monitor)

from anomaly_monitor import (
    clean_old_history,
    count_today_alerts,
    is_in_cooldown,
    record_alert,
    filter_anomalies,
    extract_anomalies,
    get_alert_config,
    load_history,
    save_history,
    load_sidecar,
    action_monitor,
    action_history,
    action_clear,
)


# ---------- fixtures ----------


@pytest.fixture
def tmp_plugin_dir(tmp_path, monkeypatch):
    """임시 플러그인 디렉토리."""
    briefings_dir = tmp_path / "briefings"
    briefings_dir.mkdir()

    monkeypatch.setattr(anomaly_monitor, "PLUGIN_DIR", str(tmp_path))
    monkeypatch.setattr(anomaly_monitor, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(anomaly_monitor, "HISTORY_PATH", str(briefings_dir / ".alert-history.json"))
    monkeypatch.setattr(anomaly_monitor, "LOG_PATH", str(briefings_dir / "schedule.log"))
    return tmp_path


@pytest.fixture
def sample_sidecar(tmp_plugin_dir):
    """이상 탐지 포함 sidecar 생성."""
    date = datetime.now().strftime("%Y-%m-%d")
    sidecar = {
        "schema_version": "1.11",
        "date": date,
        "metrics": {
            "sessions": {"current": 7500, "previous": 6000, "change_pct": 25.0},
            "bounceRate": {"current": 0.55, "previous": 0.42, "change_pct": 31.0},
        },
        "anomalies": [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": 31.0, "severity": "critical"},
        ],
    }
    (tmp_plugin_dir / "briefings" / f"{date}.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    return date, sidecar


# ---------- get_alert_config ----------


class TestGetAlertConfig:
    def test_defaults(self):
        config = get_alert_config({})
        assert config["enabled"] is True
        assert config["cooldown_hours"] == 24
        assert config["max_alerts_per_day"] == 10
        assert config["min_severity"] == "warning"

    def test_custom_config(self):
        config = get_alert_config({
            "notifications": {
                "anomaly_alerts": {
                    "enabled": False,
                    "cooldown_hours": 6,
                    "max_alerts_per_day": 5,
                    "min_severity": "critical",
                }
            }
        })
        assert config["enabled"] is False
        assert config["cooldown_hours"] == 6
        assert config["max_alerts_per_day"] == 5
        assert config["min_severity"] == "critical"


# ---------- 히스토리 관리 ----------


class TestHistory:
    def test_load_empty(self, tmp_plugin_dir):
        history = load_history()
        assert history == {"alerts": []}

    def test_save_and_load(self, tmp_plugin_dir):
        history = {"alerts": [{"metric": "sessions", "timestamp": "2026-02-26T10:00:00"}]}
        save_history(history)
        loaded = load_history()
        assert len(loaded["alerts"]) == 1
        assert loaded["alerts"][0]["metric"] == "sessions"

    def test_load_invalid_json(self, tmp_plugin_dir):
        history_path = tmp_plugin_dir / "briefings" / ".alert-history.json"
        history_path.write_text("{bad", encoding="utf-8")
        assert load_history() == {"alerts": []}

    def test_clean_old_history(self):
        now = datetime.now()
        old = (now - timedelta(days=10)).isoformat()
        recent = (now - timedelta(hours=1)).isoformat()
        history = {
            "alerts": [
                {"metric": "a", "timestamp": old},
                {"metric": "b", "timestamp": recent},
            ]
        }
        cleaned = clean_old_history(history, days=7)
        assert len(cleaned["alerts"]) == 1
        assert cleaned["alerts"][0]["metric"] == "b"

    def test_count_today_alerts(self):
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        history = {
            "alerts": [
                {"metric": "a", "timestamp": f"{today}T10:00:00"},
                {"metric": "b", "timestamp": f"{today}T11:00:00"},
                {"metric": "c", "timestamp": f"{yesterday}T10:00:00"},
            ]
        }
        assert count_today_alerts(history) == 2

    def test_is_in_cooldown_true(self):
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        history = {"alerts": [{"metric": "sessions", "timestamp": recent}]}
        assert is_in_cooldown(history, "sessions", 24) is True

    def test_is_in_cooldown_false_expired(self):
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        history = {"alerts": [{"metric": "sessions", "timestamp": old}]}
        assert is_in_cooldown(history, "sessions", 24) is False

    def test_is_in_cooldown_false_different_metric(self):
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        history = {"alerts": [{"metric": "sessions", "timestamp": recent}]}
        assert is_in_cooldown(history, "bounceRate", 24) is False

    def test_record_alert(self):
        history = {"alerts": []}
        history = record_alert(history, "sessions", 25.0, "warning")
        assert len(history["alerts"]) == 1
        assert history["alerts"][0]["metric"] == "sessions"


# ---------- filter_anomalies ----------


class TestFilterAnomalies:
    def test_basic_filtering(self):
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": 31.0, "severity": "critical"},
        ]
        history = {"alerts": []}
        config = {"cooldown_hours": 24, "max_alerts_per_day": 10, "min_severity": "warning"}
        filtered = filter_anomalies(anomalies, history, config)
        assert len(filtered) == 2

    def test_cooldown_filters_metric(self):
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
        ]
        history = {"alerts": [{"metric": "sessions", "timestamp": recent}]}
        config = {"cooldown_hours": 24, "max_alerts_per_day": 10, "min_severity": "warning"}
        filtered = filter_anomalies(anomalies, history, config)
        assert len(filtered) == 0

    def test_daily_limit(self):
        today = datetime.now().strftime("%Y-%m-%d")
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
        ]
        # 이미 3건 전송됨
        history = {"alerts": [
            {"metric": f"m{i}", "timestamp": f"{today}T{10+i}:00:00"} for i in range(3)
        ]}
        config = {"cooldown_hours": 24, "max_alerts_per_day": 3, "min_severity": "warning"}
        filtered = filter_anomalies(anomalies, history, config)
        assert len(filtered) == 0

    def test_min_severity_critical(self):
        anomalies = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning"},
            {"metric": "bounceRate", "change_pct": 31.0, "severity": "critical"},
        ]
        history = {"alerts": []}
        config = {"cooldown_hours": 24, "max_alerts_per_day": 10, "min_severity": "critical"}
        filtered = filter_anomalies(anomalies, history, config)
        assert len(filtered) == 1
        assert filtered[0]["metric"] == "bounceRate"

    def test_respects_remaining_capacity(self):
        today = datetime.now().strftime("%Y-%m-%d")
        anomalies = [
            {"metric": "a", "change_pct": 25.0, "severity": "warning"},
            {"metric": "b", "change_pct": 30.0, "severity": "warning"},
            {"metric": "c", "change_pct": 35.0, "severity": "warning"},
        ]
        # 이미 2건 전송됨, 한도 3
        history = {"alerts": [
            {"metric": f"x{i}", "timestamp": f"{today}T10:00:00"} for i in range(2)
        ]}
        config = {"cooldown_hours": 24, "max_alerts_per_day": 3, "min_severity": "warning"}
        filtered = filter_anomalies(anomalies, history, config)
        assert len(filtered) == 1


# ---------- extract_anomalies ----------


class TestExtractAnomalies:
    def test_basic(self):
        sidecar = {"anomalies": [{"metric": "sessions", "change_pct": 25.0, "severity": "warning"}]}
        result = extract_anomalies(sidecar)
        assert len(result) == 1

    def test_empty(self):
        assert extract_anomalies({"anomalies": []}) == []

    def test_missing_key(self):
        assert extract_anomalies({"metrics": {}}) == []

    def test_non_dict_sidecar(self):
        assert extract_anomalies("not a dict") == []

    def test_non_list_anomalies(self):
        assert extract_anomalies({"anomalies": "not a list"}) == []

    def test_filters_non_dict_entries(self):
        sidecar = {"anomalies": [{"metric": "a"}, 42, "bad"]}
        result = extract_anomalies(sidecar)
        assert len(result) == 1


# ---------- load_sidecar ----------


class TestLoadSidecar:
    def test_missing_file(self, tmp_plugin_dir):
        assert load_sidecar("2026-01-01") is None

    def test_valid_file(self, tmp_plugin_dir, sample_sidecar):
        date, _ = sample_sidecar
        sidecar = load_sidecar(date)
        assert sidecar is not None
        assert sidecar["date"] == date

    def test_invalid_json(self, tmp_plugin_dir):
        (tmp_plugin_dir / "briefings" / "2026-01-01.json").write_text("{bad", encoding="utf-8")
        assert load_sidecar("2026-01-01") is None


# ---------- CLI 액션 ----------


class TestActionMonitor:
    def test_no_sidecar(self, tmp_plugin_dir, capsys):
        result = action_monitor("2026-01-01")
        assert result == 2
        captured = capsys.readouterr()
        assert "찾을 수 없습니다" in captured.err

    def test_no_anomalies(self, tmp_plugin_dir, capsys):
        date = datetime.now().strftime("%Y-%m-%d")
        sidecar = {"anomalies": []}
        (tmp_plugin_dir / "briefings" / f"{date}.json").write_text(
            json.dumps(sidecar), encoding="utf-8"
        )
        result = action_monitor(date)
        assert result == 0
        captured = capsys.readouterr()
        assert "없습니다" in captured.out

    def test_alerts_disabled(self, tmp_plugin_dir, sample_sidecar, capsys):
        date, _ = sample_sidecar
        config = {"notifications": {"anomaly_alerts": {"enabled": False}}}
        (tmp_plugin_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
        result = action_monitor(date)
        assert result == 0
        captured = capsys.readouterr()
        assert "비활성화" in captured.out

    def test_all_in_cooldown(self, tmp_plugin_dir, sample_sidecar, capsys):
        date, _ = sample_sidecar
        # 최근 알림으로 쿨다운 설정
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        history = {"alerts": [
            {"metric": "sessions", "timestamp": recent},
            {"metric": "bounceRate", "timestamp": recent},
        ]}
        save_history(history)
        result = action_monitor(date)
        assert result == 0
        captured = capsys.readouterr()
        assert "필터링" in captured.out

    def test_send_success(self, tmp_plugin_dir, sample_sidecar, monkeypatch, capsys):
        date, _ = sample_sidecar
        monkeypatch.setattr(anomaly_monitor, "send_anomaly_alert", lambda a: True)
        result = action_monitor(date)
        assert result == 0
        captured = capsys.readouterr()
        assert "전송" in captured.out
        # 히스토리에 기록되었는지 확인
        history = load_history()
        assert len(history["alerts"]) == 2

    def test_send_failure(self, tmp_plugin_dir, sample_sidecar, monkeypatch, capsys):
        date, _ = sample_sidecar
        monkeypatch.setattr(anomaly_monitor, "send_anomaly_alert", lambda a: False)
        result = action_monitor(date)
        assert result == 1
        captured = capsys.readouterr()
        assert "실패" in captured.err


class TestActionHistory:
    def test_empty_history(self, tmp_plugin_dir, capsys):
        result = action_history()
        assert result == 0
        captured = capsys.readouterr()
        assert "없습니다" in captured.out

    def test_with_history(self, tmp_plugin_dir, capsys):
        history = {"alerts": [
            {"metric": "sessions", "change_pct": 25.0, "severity": "warning",
             "timestamp": "2026-02-26T10:00:00"},
        ]}
        save_history(history)
        result = action_history()
        assert result == 0
        captured = capsys.readouterr()
        assert "sessions" in captured.out
        assert "+25.0%" in captured.out


class TestActionClear:
    def test_clear(self, tmp_plugin_dir, capsys):
        history = {"alerts": [{"metric": "a", "timestamp": "2026-02-26T10:00:00"}]}
        save_history(history)
        result = action_clear()
        assert result == 0
        loaded = load_history()
        assert len(loaded["alerts"]) == 0
        captured = capsys.readouterr()
        assert "초기화" in captured.out
