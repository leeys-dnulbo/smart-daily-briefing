"""tests/test_migrate_config.py — scripts/migrate-config.py 테스트"""

import importlib.util
import json
import os
import sys

import pytest

# 파일명에 하이픈이 있어서 importlib로 로드
_spec = importlib.util.spec_from_file_location(
    "migrate_config",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "migrate-config.py"),
)
migrate_config_mod = importlib.util.module_from_spec(_spec)
sys.modules["migrate_config"] = migrate_config_mod
_spec.loader.exec_module(migrate_config_mod)

from migrate_config import backup_config, main, migrate_config, _migrate_v20_to_v21


# ========== helpers ==========

def _default_slack():
    return {"enabled": False, "webhook_url": ""}


def _default_telegram():
    return {"enabled": False, "bot_token": "", "chat_id": ""}


def _default_discord():
    return {"enabled": False, "webhook_url": ""}


def _default_anomaly_alerts():
    return {
        "enabled": True,
        "cooldown_hours": 4,
        "max_alerts_per_day": 10,
        "min_severity": "warning",
    }


# ========== migrate_config 함수 ==========


class TestMigrateConfig:
    """migrate_config() 단위 테스트."""

    def test_v1_minimal_adds_all_sections(self):
        """v1.0 최소 config -> 모든 섹션 추가 + v2.1로 마이그레이션."""
        config = {"version": "1.0"}
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert migrated["notifications"]["slack"] == _default_slack()
        assert migrated["notifications"]["telegram"] == _default_telegram()
        assert migrated["notifications"]["discord"] == _default_discord()
        assert migrated["notifications"]["anomaly_alerts"] == _default_anomaly_alerts()
        # v2.1 필드
        assert migrated["briefing"]["custom_sections"] == []
        assert migrated["presets"]["custom"] == {}
        assert any("version" in c for c in changes)
        assert any("notifications" in c for c in changes)
        assert any("slack" in c for c in changes)
        assert any("telegram" in c for c in changes)
        assert any("discord" in c for c in changes)
        assert any("anomaly_alerts" in c for c in changes)
        assert any("custom_sections" in c for c in changes)
        assert any("presets" in c for c in changes)

    def test_v1_11_with_slack_preserves_slack(self):
        """v1.11 config에 slack 있으면 보존, telegram/discord 추가, v2.1로."""
        existing_slack = {"enabled": True, "webhook_url": "https://hooks.slack.com/xxx"}
        config = {
            "version": "1.11",
            "notifications": {"slack": existing_slack},
        }
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert migrated["notifications"]["slack"] == existing_slack
        assert migrated["notifications"]["telegram"] == _default_telegram()
        assert migrated["notifications"]["discord"] == _default_discord()
        # slack은 이미 있으므로 slack 추가 변경이 없어야 함
        assert not any("slack" in c for c in changes)
        assert any("telegram" in c for c in changes)
        assert any("discord" in c for c in changes)

    def test_v1_12_with_anomaly_alerts_preserves(self):
        """v1.12 config에 anomaly_alerts 있으면 보존."""
        custom_alerts = {
            "enabled": False,
            "cooldown_hours": 8,
            "max_alerts_per_day": 5,
            "min_severity": "critical",
        }
        config = {
            "version": "1.12",
            "notifications": {"anomaly_alerts": custom_alerts},
        }
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert migrated["notifications"]["anomaly_alerts"] == custom_alerts
        assert not any("anomaly_alerts" in c for c in changes)

    def test_already_v2_1_returns_message(self):
        """이미 v2.1이면 '이미 v2.1' 메시지 반환."""
        config = {"version": "2.1", "notifications": {}}
        migrated, changes = migrate_config(config)

        assert migrated is config  # 동일 객체 반환 (deep copy 안 함)
        assert len(changes) == 1
        assert "이미 v2.1" in changes[0]

    def test_empty_config_adds_all(self):
        """빈 config {} -> 모든 섹션 추가 + v2.1."""
        config = {}
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert "notifications" in migrated
        assert migrated["notifications"]["slack"] == _default_slack()
        assert migrated["notifications"]["telegram"] == _default_telegram()
        assert migrated["notifications"]["discord"] == _default_discord()
        assert migrated["notifications"]["anomaly_alerts"] == _default_anomaly_alerts()
        assert migrated["briefing"]["custom_sections"] == []
        assert migrated["presets"]["custom"] == {}
        # version 변경 로그에 "(없음)" 포함
        assert any("(없음)" in c for c in changes)

    def test_extra_unknown_fields_preserved(self):
        """알 수 없는 필드도 보존."""
        config = {
            "version": "1.0",
            "custom_field": "keep_me",
            "notifications": {
                "slack": {"enabled": True, "webhook_url": "url", "extra": 42},
            },
        }
        migrated, changes = migrate_config(config)

        assert migrated["custom_field"] == "keep_me"
        assert migrated["notifications"]["slack"]["extra"] == 42

    def test_no_version_field_treated_as_empty(self):
        """version 필드가 없으면 빈 버전으로 처리."""
        config = {"notifications": {"slack": {"enabled": True, "webhook_url": "url"}}}
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        version_change = [c for c in changes if "(없음)" in c][0]
        assert "(없음)" in version_change

    def test_original_config_not_mutated(self):
        """원본 config dict가 변경되지 않아야 함."""
        config = {"version": "1.0"}
        original_copy = json.loads(json.dumps(config))
        migrate_config(config)

        assert config == original_copy

    def test_all_notification_channels_present(self):
        """마이그레이션 후 모든 채널이 존재해야 함."""
        config = {"version": "1.5"}
        migrated, _ = migrate_config(config)

        notif = migrated["notifications"]
        assert set(notif.keys()) == {"slack", "telegram", "discord", "anomaly_alerts"}


# ========== backup_config 함수 ==========


class TestBackupConfig:
    """backup_config() 테스트."""

    def test_creates_bak_file(self, tmp_path):
        """config.json.bak 파일 생성."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"version": "1.0"}', encoding="utf-8")

        backup_path = backup_config(str(config_path))

        assert os.path.exists(backup_path)
        assert backup_path == str(config_path) + ".bak"

    def test_bak_identical_to_original(self, tmp_path):
        """백업 내용이 원본과 동일."""
        content = '{"version": "1.0", "data": "hello"}'
        config_path = tmp_path / "config.json"
        config_path.write_text(content, encoding="utf-8")

        backup_path = backup_config(str(config_path))

        with open(backup_path, encoding="utf-8") as f:
            assert f.read() == content


# ========== main() CLI 함수 ==========


class TestMain:
    """main() CLI 통합 테스트."""

    def _write_config(self, path, data):
        """헬퍼: config.json 파일 작성."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def test_dry_run_prints_changes_without_modifying(self, tmp_path, monkeypatch, capsys):
        """--dry-run은 변경 사항 출력만 하고 파일 수정 안 함."""
        config_path = tmp_path / "config.json"
        original = {"version": "1.0"}
        self._write_config(str(config_path), original)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--dry-run", "--config", str(config_path)])
        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "version" in captured.out

        # 파일이 변경되지 않아야 함
        with open(config_path, encoding="utf-8") as f:
            assert json.load(f) == original

        # .bak 파일이 생성되지 않아야 함
        assert not os.path.exists(str(config_path) + ".bak")

    def test_normal_run_creates_backup_and_migrates(self, tmp_path, monkeypatch, capsys):
        """정상 실행 시 백업 생성 후 마이그레이션."""
        config_path = tmp_path / "config.json"
        original = {"version": "1.0"}
        self._write_config(str(config_path), original)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code = main()

        assert exit_code == 0

        # 백업 확인
        bak_path = str(config_path) + ".bak"
        assert os.path.exists(bak_path)
        with open(bak_path, encoding="utf-8") as f:
            assert json.load(f) == original

        # 마이그레이션 결과 확인
        with open(config_path, encoding="utf-8") as f:
            migrated = json.load(f)
        assert migrated["version"] == "2.1"
        assert "notifications" in migrated
        assert migrated["briefing"]["custom_sections"] == []
        assert migrated["presets"]["custom"] == {}

        captured = capsys.readouterr()
        assert "마이그레이션 완료" in captured.out

    def test_missing_config_returns_exit_2(self, tmp_path, monkeypatch, capsys):
        """config.json이 없으면 exit code 2."""
        nonexistent = tmp_path / "no-such-config.json"
        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(nonexistent)])
        exit_code = main()

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "찾을 수 없습니다" in captured.err

    def test_invalid_json_returns_exit_2(self, tmp_path, monkeypatch, capsys):
        """잘못된 JSON이면 exit code 2."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{invalid json!!!", encoding="utf-8")

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code = main()

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "파싱 실패" in captured.err
        assert "수동 마이그레이션 가이드" in captured.err

    def test_idempotent_running_twice(self, tmp_path, monkeypatch, capsys):
        """두 번 실행해도 동일 결과."""
        config_path = tmp_path / "config.json"
        original = {"version": "1.0"}
        self._write_config(str(config_path), original)

        # 1차 실행
        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code1 = main()
        assert exit_code1 == 0

        with open(config_path, encoding="utf-8") as f:
            first_result = json.load(f)

        # 2차 실행
        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code2 = main()
        assert exit_code2 == 0

        with open(config_path, encoding="utf-8") as f:
            second_result = json.load(f)

        assert first_result == second_result

    def test_dry_run_already_v2_1_shows_no_changes(self, tmp_path, monkeypatch, capsys):
        """이미 v2.1인 config에 --dry-run 실행 시 '변경 사항 없음' 표시."""
        config_path = tmp_path / "config.json"
        self._write_config(str(config_path), {"version": "2.1", "notifications": {}})

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--dry-run", "--config", str(config_path)])
        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "변경 사항 없음" in captured.out

    def test_normal_run_already_v2_1_skips_backup(self, tmp_path, monkeypatch, capsys):
        """이미 v2.1이면 백업/파일쓰기 없이 즉시 종료."""
        config_path = tmp_path / "config.json"
        v21_config = {"version": "2.1", "notifications": {"slack": {"enabled": True, "webhook_url": "url"}}}
        self._write_config(str(config_path), v21_config)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code = main()
        assert exit_code == 0

        # 이미 v2.1이면 백업 생성하지 않음
        assert not os.path.exists(str(config_path) + ".bak")
        captured = capsys.readouterr()
        assert "이미 v2.1" in captured.out

    def test_full_v1_config_migration(self, tmp_path, monkeypatch, capsys):
        """실제 v1 config 전체 마이그레이션 시나리오."""
        config_path = tmp_path / "config.json"
        v1_config = {
            "version": "1.11",
            "ga4_property_id": "properties/12345",
            "timezone": "Asia/Seoul",
            "notifications": {
                "slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/xxx"},
            },
        }
        self._write_config(str(config_path), v1_config)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code = main()
        assert exit_code == 0

        with open(config_path, encoding="utf-8") as f:
            result = json.load(f)

        # 기존 필드 보존
        assert result["ga4_property_id"] == "properties/12345"
        assert result["timezone"] == "Asia/Seoul"
        assert result["notifications"]["slack"]["enabled"] is True
        assert result["notifications"]["slack"]["webhook_url"] == "https://hooks.slack.com/xxx"
        # 새 섹션 추가
        assert result["version"] == "2.1"
        assert "telegram" in result["notifications"]
        assert "discord" in result["notifications"]
        assert "anomaly_alerts" in result["notifications"]
        assert result["briefing"]["custom_sections"] == []
        assert result["presets"]["custom"] == {}


# ========== v2.0 → v2.1 마이그레이션 테스트 ==========


class TestMigrateV20ToV21:
    """v2.0 → v2.1 마이그레이션 전용 테스트."""

    def test_v2_0_adds_custom_sections_and_presets(self):
        """v2.0 config에 custom_sections, presets.custom 추가."""
        config = {
            "version": "2.0",
            "briefing": {
                "sections": [{"id": "overview", "enabled": True}],
            },
            "notifications": {},
        }
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert migrated["briefing"]["custom_sections"] == []
        assert migrated["presets"]["custom"] == {}
        assert any("custom_sections" in c for c in changes)
        assert any("presets" in c for c in changes)

    def test_v2_0_preserves_existing_briefing_sections(self):
        """v2.0 → v2.1 시 기존 briefing.sections 보존."""
        sections = [
            {"id": "overview", "enabled": True, "metrics": ["sessions"]},
            {"id": "top_pages", "enabled": False, "metrics": ["screenPageViews"]},
        ]
        config = {
            "version": "2.0",
            "briefing": {"sections": sections},
            "notifications": {},
        }
        migrated, _ = migrate_config(config)

        assert migrated["briefing"]["sections"] == sections
        assert migrated["briefing"]["custom_sections"] == []

    def test_v2_0_removes_custom_preset_base(self):
        """v2.0에 custom_preset_base가 있으면 제거."""
        config = {
            "version": "2.0",
            "custom_preset_base": "marketing",
            "notifications": {},
        }
        migrated, changes = migrate_config(config)

        assert "custom_preset_base" not in migrated
        assert any("custom_preset_base" in c for c in changes)

    def test_v2_0_without_briefing_creates_briefing(self):
        """v2.0에 briefing 키가 없어도 custom_sections 추가."""
        config = {"version": "2.0", "notifications": {}}
        migrated, changes = migrate_config(config)

        assert migrated["briefing"]["custom_sections"] == []
        assert any("custom_sections" in c for c in changes)

    def test_v1_to_v2_1_full_chain(self):
        """v1.x → v2.0 → v2.1 전체 체인 마이그레이션."""
        config = {"version": "1.5"}
        migrated, changes = migrate_config(config)

        # v2.0 단계 변경
        assert any("1.5 -> 2.0" in c for c in changes)
        assert "notifications" in migrated

        # v2.1 단계 변경
        assert migrated["version"] == "2.1"
        assert any("2.0 -> 2.1" in c for c in changes)
        assert migrated["briefing"]["custom_sections"] == []
        assert migrated["presets"]["custom"] == {}

    def test_v2_0_with_presets_but_no_custom_adds_custom(self):
        """v2.0에 presets 키는 있지만 custom 서브키가 없을 때 custom 추가."""
        config = {
            "version": "2.0",
            "presets": {"other_key": "value"},
            "briefing": {"sections": []},
            "notifications": {},
        }
        migrated, changes = migrate_config(config)

        assert migrated["version"] == "2.1"
        assert migrated["presets"]["custom"] == {}
        # 기존 키 보존
        assert migrated["presets"]["other_key"] == "value"
        assert any("presets.custom" in c for c in changes)

    def test_original_not_mutated_v20_to_v21(self):
        """v2.0 원본이 마이그레이션 후에도 변경되지 않아야 함."""
        config = {"version": "2.0", "briefing": {"sections": []}, "notifications": {}}
        original_copy = json.loads(json.dumps(config))
        migrate_config(config)

        assert config == original_copy

    def test_v2_0_to_v2_1_main_normal_run(self, tmp_path, monkeypatch, capsys):
        """v2.0 config를 main()으로 v2.1로 마이그레이션."""
        config_path = tmp_path / "config.json"
        v20_config = {"version": "2.0", "notifications": {}, "briefing": {"sections": []}}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(v20_config, f)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--config", str(config_path)])
        exit_code = main()
        assert exit_code == 0

        with open(config_path, encoding="utf-8") as f:
            result = json.load(f)
        assert result["version"] == "2.1"
        assert result["briefing"]["custom_sections"] == []
        assert result["presets"]["custom"] == {}

        captured = capsys.readouterr()
        assert "마이그레이션 완료" in captured.out

    def test_dry_run_v2_0_shows_v2_1_changes(self, tmp_path, monkeypatch, capsys):
        """v2.0 config에 --dry-run 시 v2.1 변경 사항 표시."""
        config_path = tmp_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"version": "2.0", "notifications": {}}, f)

        monkeypatch.setattr(sys, "argv", ["migrate-config.py", "--dry-run", "--config", str(config_path)])
        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "2.0 -> 2.1" in captured.out
        assert "custom_sections" in captured.out

        # 파일 변경 안 됨
        with open(config_path, encoding="utf-8") as f:
            assert json.load(f)["version"] == "2.0"
