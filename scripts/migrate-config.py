#!/usr/bin/env python3
"""
Smart Daily Briefing - config.json 마이그레이션 (v1.x → v2.0 → v2.1)

체인 마이그레이션으로 config.json을 최신 버전(v2.1)으로 업데이트합니다.
- v1.x → v2.0: Telegram/Discord 채널 섹션 추가
- v2.0 → v2.1: custom_sections, presets.custom 추가

Usage:
    python3 scripts/migrate-config.py              # 마이그레이션 실행
    python3 scripts/migrate-config.py --dry-run     # 변경 사항만 출력
    python3 scripts/migrate-config.py --config PATH # 경로 지정
"""

import json
import os
import shutil
import sys
import tempfile


def _find_plugin_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _migrate_v1x_to_v20(migrated, old_version):
    """v1.x → v2.0 마이그레이션 로직. migrated를 in-place 수정."""
    changes = []

    migrated["version"] = "2.0"
    changes.append(f"version: {old_version} -> 2.0")

    # notifications 섹션 확보
    if "notifications" not in migrated:
        migrated["notifications"] = {}
        changes.append("notifications 섹션 추가")

    notif = migrated["notifications"]

    # slack 기본 구조 확보
    if "slack" not in notif:
        notif["slack"] = {"enabled": False, "webhook_url": ""}
        changes.append("slack 섹션 추가 (비활성)")

    # telegram 추가
    if "telegram" not in notif:
        notif["telegram"] = {"enabled": False, "bot_token": "", "chat_id": ""}
        changes.append("telegram 섹션 추가 (비활성)")

    # discord 추가
    if "discord" not in notif:
        notif["discord"] = {"enabled": False, "webhook_url": ""}
        changes.append("discord 섹션 추가 (비활성)")

    # anomaly_alerts 기본값 확보
    if "anomaly_alerts" not in notif:
        notif["anomaly_alerts"] = {
            "enabled": True,
            "cooldown_hours": 4,
            "max_alerts_per_day": 10,
            "min_severity": "warning",
        }
        changes.append("anomaly_alerts 섹션 추가")

    return changes


def _migrate_v20_to_v21(migrated):
    """v2.0 → v2.1 마이그레이션 로직. migrated를 in-place 수정."""
    changes = []

    migrated["version"] = "2.1"
    changes.append("version: 2.0 -> 2.1")

    # briefing.custom_sections 추가
    briefing = migrated.get("briefing", {})
    if "custom_sections" not in briefing:
        briefing["custom_sections"] = []
        if "briefing" not in migrated:
            migrated["briefing"] = briefing
        changes.append("briefing.custom_sections 추가")

    # presets.custom 추가
    if "presets" not in migrated:
        migrated["presets"] = {"custom": {}}
        changes.append("presets.custom 추가")
    elif "custom" not in migrated["presets"]:
        migrated["presets"]["custom"] = {}
        changes.append("presets.custom 추가")

    # custom_preset_base 필드 제거 (과도기 필드)
    if "custom_preset_base" in migrated:
        del migrated["custom_preset_base"]
        changes.append("custom_preset_base 필드 제거")

    return changes


def migrate_config(config):
    """config dict를 최신 형식(v2.1)으로 체인 마이그레이션.

    Returns:
        (migrated_config, list_of_changes)
    """
    version = config.get("version", "")

    if version == "2.1":
        return config, ["이미 v2.1입니다"]

    # 원본 보호를 위해 deep copy
    migrated = json.loads(json.dumps(config))
    changes = []

    # Step 1: v1.x → v2.0 (v2.0 미만인 경우)
    if version != "2.0":
        old_version = version or "(없음)"
        changes.extend(_migrate_v1x_to_v20(migrated, old_version))

    # Step 2: v2.0 → v2.1
    changes.extend(_migrate_v20_to_v21(migrated))

    return migrated, changes


def backup_config(config_path):
    """config.json을 .bak으로 백업. 백업 경로 반환."""
    backup_path = config_path + ".bak"
    shutil.copy2(config_path, backup_path)
    return backup_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="config.json v1.x → v2.1 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="변경 사항만 출력 (파일 수정 안 함)")
    parser.add_argument("--config", type=str, help="config.json 경로")
    args = parser.parse_args()

    plugin_dir = _find_plugin_dir()
    config_path = args.config or os.path.join(plugin_dir, "config.json")

    if not os.path.exists(config_path):
        print(f"config.json을 찾을 수 없습니다: {config_path}", file=sys.stderr)
        return 2

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"config.json 파싱 실패: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("수동 마이그레이션 가이드:", file=sys.stderr)
        print("  config.json.example을 참고하여 직접 수정하세요.", file=sys.stderr)
        return 2

    if not isinstance(config, dict):
        print("config.json이 JSON 객체가 아닙니다.", file=sys.stderr)
        return 2

    migrated, changes = migrate_config(config)
    is_already_latest = len(changes) == 1 and "이미 v2.1" in changes[0]

    if args.dry_run:
        print("=== 마이그레이션 미리보기 (dry-run) ===")
        for c in changes:
            print(f"  - {c}")
        if is_already_latest:
            print("\n변경 사항 없음.")
        else:
            print(f"\n총 {len(changes)}건의 변경이 적용됩니다.")
        return 0

    # 이미 최신이면 파일 수정/백업 불필요
    if is_already_latest:
        print("이미 v2.1입니다. 변경 사항 없음.")
        return 0

    # 백업
    backup_path = backup_config(config_path)
    print(f"백업 생성: {backup_path}")

    # atomic write
    config_dir = os.path.dirname(config_path)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=config_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(migrated, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, config_path)
        tmp = None
    except OSError as e:
        print(f"마이그레이션 실패: {e}", file=sys.stderr)
        print(f"원본 복원: cp {backup_path} {config_path}", file=sys.stderr)
        return 1
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass

    print("마이그레이션 완료:")
    for c in changes:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
