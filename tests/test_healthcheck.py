"""tests/test_healthcheck.py — scripts/healthcheck.py 테스트"""

import json
import os
import sys
import textwrap

import pytest

# healthcheck.py를 import할 수 있도록 scripts 디렉토리를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from healthcheck import (
    ALL_CHECKS,
    CHECK_MAP,
    ConfigCheck,
    FontCheck,
    HealthCheckItem,
    MatplotlibCheck,
    PythonEnvCheck,
    ScriptsCheck,
    SidecarCheck,
    SlackCheck,
    WeasyprintCheck,
    format_json,
    format_text,
    get_exit_code,
    run_healthcheck,
)


# ---------- fixtures ----------


@pytest.fixture
def tmp_plugin_dir(tmp_path):
    """임시 플러그인 디렉토리를 생성한다."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    briefings_dir = tmp_path / "briefings"
    briefings_dir.mkdir()
    return tmp_path


@pytest.fixture
def ctx(tmp_plugin_dir):
    """헬스체크 컨텍스트."""
    return {"plugin_dir": str(tmp_plugin_dir)}


# ---------- HealthCheckItem 인터페이스 ----------


class TestHealthCheckItem:
    def test_base_class_not_implemented(self):
        item = HealthCheckItem()
        with pytest.raises(NotImplementedError):
            item.check({})

    def test_all_checks_have_name_and_key(self):
        for check in ALL_CHECKS:
            assert check.name, f"{check.__class__.__name__} has no name"
            assert check.key, f"{check.__class__.__name__} has no key"

    def test_check_map_matches_all_checks(self):
        assert len(CHECK_MAP) == len(ALL_CHECKS)
        for check in ALL_CHECKS:
            assert check.key in CHECK_MAP

    def test_all_checks_unique_keys(self):
        keys = [c.key for c in ALL_CHECKS]
        assert len(keys) == len(set(keys)), "Duplicate keys found"


# ---------- ConfigCheck ----------


class TestConfigCheck:
    def test_no_config_returns_warn(self, ctx):
        status, msg = ConfigCheck().check(ctx)
        assert status == "WARN"
        assert "없음" in msg

    def test_valid_config(self, ctx, tmp_plugin_dir):
        config = {"version": "1.11", "preset": "default"}
        (tmp_plugin_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        status, msg = ConfigCheck().check(ctx)
        assert status == "OK"
        assert "1.11" in msg

    def test_invalid_json_returns_fail(self, ctx, tmp_plugin_dir):
        (tmp_plugin_dir / "config.json").write_text("{invalid", encoding="utf-8")
        status, msg = ConfigCheck().check(ctx)
        assert status == "FAIL"
        assert "파싱" in msg


# ---------- PythonEnvCheck ----------


class TestPythonEnvCheck:
    def test_returns_ok_for_current_python(self, ctx):
        status, msg = PythonEnvCheck().check(ctx)
        # 테스트 환경에서는 Python 3.9+ 이므로 OK
        if sys.version_info >= (3, 9):
            assert status == "OK"
        else:
            assert status == "WARN"
        assert str(sys.version_info.major) in msg


# ---------- SlackCheck ----------


class TestSlackCheck:
    def test_no_config_returns_skip(self, ctx):
        status, msg = SlackCheck().check(ctx)
        assert status == "SKIP"

    def test_no_webhook_returns_skip(self, ctx, tmp_plugin_dir):
        config = {"notifications": {"slack": {}}}
        (tmp_plugin_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        status, msg = SlackCheck().check(ctx)
        assert status == "SKIP"

    def test_invalid_url_returns_fail(self, ctx, tmp_plugin_dir):
        config = {"notifications": {"slack": {"webhook_url": "http://not-https.com"}}}
        (tmp_plugin_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        status, msg = SlackCheck().check(ctx)
        assert status == "FAIL"
        assert "잘못된 URL" in msg


# ---------- SidecarCheck ----------


class TestSidecarCheck:
    def test_no_briefings_dir_returns_warn(self, ctx, tmp_plugin_dir):
        # briefings 디렉토리 삭제
        (tmp_plugin_dir / "briefings").rmdir()
        status, msg = SidecarCheck().check(ctx)
        assert status == "WARN"
        assert "디렉토리" in msg

    def test_no_recent_sidecars(self, ctx):
        status, msg = SidecarCheck().check(ctx)
        assert status == "WARN"
        assert "없음" in msg

    def test_some_sidecars(self, ctx, tmp_plugin_dir):
        from datetime import datetime, timedelta

        briefings_dir = tmp_plugin_dir / "briefings"
        # 최근 3일 sidecar 생성
        for i in range(3):
            d = datetime.now() - timedelta(days=i + 1)
            (briefings_dir / f"{d.strftime('%Y-%m-%d')}.json").write_text("{}")
        status, msg = SidecarCheck().check(ctx)
        assert status == "WARN"
        assert "3일만" in msg

    def test_enough_sidecars(self, ctx, tmp_plugin_dir):
        from datetime import datetime, timedelta

        briefings_dir = tmp_plugin_dir / "briefings"
        # 최근 6일 sidecar 생성
        for i in range(6):
            d = datetime.now() - timedelta(days=i + 1)
            (briefings_dir / f"{d.strftime('%Y-%m-%d')}.json").write_text("{}")
        status, msg = SidecarCheck().check(ctx)
        assert status == "OK"
        assert "6일" in msg


# ---------- ScriptsCheck ----------


class TestScriptsCheck:
    def test_missing_all_scripts(self, ctx):
        status, msg = ScriptsCheck().check(ctx)
        assert status == "FAIL"
        assert "누락" in msg

    def test_all_scripts_present(self, ctx, tmp_plugin_dir):
        scripts_dir = tmp_plugin_dir / "scripts"
        for name in [
            "generate-charts.py",
            "generate-pdf.py",
            "manage-schedule.sh",
            "send-slack.sh",
        ]:
            (scripts_dir / name).write_text("#!/bin/bash")
        status, msg = ScriptsCheck().check(ctx)
        assert status == "OK"
        assert "4개" in msg

    def test_partial_scripts(self, ctx, tmp_plugin_dir):
        scripts_dir = tmp_plugin_dir / "scripts"
        (scripts_dir / "generate-charts.py").write_text("#!/usr/bin/env python3")
        status, msg = ScriptsCheck().check(ctx)
        assert status == "FAIL"
        # 3개 누락
        assert "generate-pdf.py" in msg


# ---------- run_healthcheck ----------


class TestRunHealthcheck:
    def test_full_run(self, tmp_plugin_dir):
        results = run_healthcheck(str(tmp_plugin_dir))
        assert len(results) == len(ALL_CHECKS)
        for key, name, status, message in results:
            assert status in ("OK", "WARN", "FAIL", "SKIP")

    def test_filtered_run(self, tmp_plugin_dir):
        results = run_healthcheck(str(tmp_plugin_dir), checks=["config", "python"])
        assert len(results) == 2
        keys = [r[0] for r in results]
        assert "config" in keys
        assert "python" in keys

    def test_unknown_check_ignored(self, tmp_plugin_dir):
        results = run_healthcheck(str(tmp_plugin_dir), checks=["nonexistent"])
        assert len(results) == 0

    def test_exception_in_check_returns_fail(self, tmp_plugin_dir):
        """체크 실행 중 예외 발생 시 FAIL을 반환한다."""

        class BrokenCheck(HealthCheckItem):
            name = "broken"
            key = "broken"

            def check(self, ctx):
                raise RuntimeError("test error")

        # 직접 호출하여 예외 처리 확인
        ctx = {"plugin_dir": str(tmp_plugin_dir)}
        try:
            status, message = BrokenCheck().check(ctx)
        except RuntimeError:
            # run_healthcheck에서 감싸므로 직접 호출 시 예외 발생
            pass

        # run_healthcheck 경유 시 예외가 잡혀야 함
        import healthcheck as hc

        original = hc.ALL_CHECKS
        try:
            hc.ALL_CHECKS = [BrokenCheck()]
            results = hc.run_healthcheck(str(tmp_plugin_dir))
            assert len(results) == 1
            assert results[0][2] == "FAIL"
            assert "예외" in results[0][3]
        finally:
            hc.ALL_CHECKS = original


# ---------- 출력 포맷 ----------


class TestFormatters:
    def test_format_text(self):
        results = [
            ("config", "config.json", "OK", "유효"),
            ("python", "Python 환경", "WARN", "3.8"),
            ("slack", "Slack webhook", "SKIP", "미설정"),
        ]
        output = format_text(results)
        assert "환경 진단" in output
        assert "[OK]" in output
        assert "[WARN]" in output
        assert "[SKIP]" in output
        assert "1 정상" in output
        assert "1 경고" in output
        assert "1 건너뜀" in output

    def test_format_json(self):
        results = [
            ("config", "config.json", "OK", "유효"),
        ]
        output = format_json(results)
        data = json.loads(output)
        assert "config" in data
        assert data["config"]["status"] == "OK"

    def test_format_text_no_results(self):
        output = format_text([])
        assert "환경 진단" in output


# ---------- exit code ----------


class TestExitCode:
    def test_all_ok(self):
        results = [("a", "a", "OK", "ok"), ("b", "b", "OK", "ok")]
        assert get_exit_code(results) == 0

    def test_warn_returns_1(self):
        results = [("a", "a", "OK", "ok"), ("b", "b", "WARN", "warn")]
        assert get_exit_code(results) == 1

    def test_fail_returns_2(self):
        results = [("a", "a", "OK", "ok"), ("b", "b", "FAIL", "fail")]
        assert get_exit_code(results) == 2

    def test_fail_takes_precedence(self):
        results = [("a", "a", "WARN", "w"), ("b", "b", "FAIL", "f")]
        assert get_exit_code(results) == 2

    def test_skip_only_returns_0(self):
        results = [("a", "a", "SKIP", "skip")]
        assert get_exit_code(results) == 0
