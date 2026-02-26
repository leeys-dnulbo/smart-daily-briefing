"""tests/test_healthcheck.py — scripts/healthcheck.py 테스트"""

import json
import os
import subprocess
import sys

import pytest

# conftest.py가 이미 scripts/ 디렉토리를 sys.path에 추가함

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
        if sys.version_info >= (3, 9):
            assert status == "OK"
        else:
            assert status == "WARN"
        assert str(sys.version_info.major) in msg


# ---------- MatplotlibCheck ----------


class TestMatplotlibCheck:
    def test_installed(self, ctx, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "3.8.0\n"})(),
        )
        status, msg = MatplotlibCheck().check(ctx)
        assert status == "OK"
        assert "3.8.0" in msg

    def test_not_installed(self, ctx, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})(),
        )
        status, msg = MatplotlibCheck().check(ctx)
        assert status == "WARN"
        assert "미설치" in msg

    def test_timeout(self, ctx, monkeypatch):
        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired("cmd", 10)
        monkeypatch.setattr(subprocess, "run", raise_timeout)
        status, msg = MatplotlibCheck().check(ctx)
        assert status == "WARN"
        assert "확인 불가" in msg


# ---------- WeasyprintCheck ----------


class TestWeasyprintCheck:
    def test_installed(self, ctx, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "60.1\n"})(),
        )
        status, msg = WeasyprintCheck().check(ctx)
        assert status == "OK"
        assert "60.1" in msg

    def test_not_installed(self, ctx, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})(),
        )
        status, msg = WeasyprintCheck().check(ctx)
        assert status == "WARN"
        assert "미설치" in msg


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

    def test_invalid_url_returns_fail_no_url_leak(self, ctx, tmp_plugin_dir):
        config = {"notifications": {"slack": {"webhook_url": "http://not-https.com/secret"}}}
        (tmp_plugin_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        status, msg = SlackCheck().check(ctx)
        assert status == "FAIL"
        # URL이 에러 메시지에 노출되지 않아야 함
        assert "not-https" not in msg
        assert "secret" not in msg
        assert "https://" in msg

    def test_malformed_config_returns_fail(self, ctx, tmp_plugin_dir):
        (tmp_plugin_dir / "config.json").write_text("{bad json", encoding="utf-8")
        status, msg = SlackCheck().check(ctx)
        assert status == "FAIL"
        assert "파싱" in msg

    def test_connection_success(self, ctx, tmp_plugin_dir, monkeypatch):
        config = {"notifications": {"slack": {"webhook_url": "https://hooks.slack.com/test"}}}
        (tmp_plugin_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        status, msg = SlackCheck().check(ctx)
        assert status == "OK"
        assert "연결됨" in msg

    def test_connection_server_error(self, ctx, tmp_plugin_dir, monkeypatch):
        config = {"notifications": {"slack": {"webhook_url": "https://hooks.slack.com/test"}}}
        (tmp_plugin_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        class MockResp:
            status = 500
            def __enter__(self): return self
            def __exit__(self, *a): pass

        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        status, msg = SlackCheck().check(ctx)
        assert status == "FAIL"
        assert "500" in msg

    def test_connection_exception(self, ctx, tmp_plugin_dir, monkeypatch):
        config = {"notifications": {"slack": {"webhook_url": "https://hooks.slack.com/test"}}}
        (tmp_plugin_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        def raise_connection_error(*a, **kw):
            raise ConnectionError("timeout")

        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", raise_connection_error)
        status, msg = SlackCheck().check(ctx)
        assert status == "WARN"
        assert "ConnectionError" in msg


# ---------- SidecarCheck ----------


class TestSidecarCheck:
    def test_no_briefings_dir_returns_warn(self, ctx, tmp_plugin_dir):
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
        for i in range(3):
            d = datetime.now() - timedelta(days=i + 1)
            (briefings_dir / f"{d.strftime('%Y-%m-%d')}.json").write_text("{}")
        status, msg = SidecarCheck().check(ctx)
        assert status == "WARN"
        assert "3" in msg

    def test_enough_sidecars(self, ctx, tmp_plugin_dir):
        from datetime import datetime, timedelta

        briefings_dir = tmp_plugin_dir / "briefings"
        for i in range(6):
            d = datetime.now() - timedelta(days=i + 1)
            (briefings_dir / f"{d.strftime('%Y-%m-%d')}.json").write_text("{}")
        status, msg = SidecarCheck().check(ctx)
        assert status == "OK"
        assert "6" in msg


# ---------- FontCheck ----------


class TestFontCheck:
    def test_utils_not_found(self, ctx):
        """utils.py가 없으면 WARN"""
        status, msg = FontCheck().check(ctx)
        assert status == "WARN"
        assert "없음" in msg

    def test_font_found(self, ctx, tmp_plugin_dir, monkeypatch):
        """find_korean_font가 경로를 반환하면 OK"""
        scripts_dir = tmp_plugin_dir / "scripts"
        # 최소한의 utils.py 모킹
        (scripts_dir / "utils.py").write_text(
            "def find_korean_font(): return '/fonts/NanumGothic.ttf'\n"
        )
        status, msg = FontCheck().check(ctx)
        assert status == "OK"
        assert "NanumGothic" in msg

    def test_font_not_found(self, ctx, tmp_plugin_dir):
        scripts_dir = tmp_plugin_dir / "scripts"
        (scripts_dir / "utils.py").write_text(
            "def find_korean_font(): return None\n"
        )
        status, msg = FontCheck().check(ctx)
        assert status == "WARN"
        assert "찾을 수 없음" in msg


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

    def test_unknown_check_returns_fail(self, tmp_plugin_dir):
        """존재하지 않는 체크 키는 FAIL 결과를 반환한다."""
        results = run_healthcheck(str(tmp_plugin_dir), checks=["nonexistent"])
        assert len(results) == 1
        assert results[0][2] == "FAIL"
        assert "알 수 없는" in results[0][3]

    def test_exception_in_check_returns_fail(self, tmp_plugin_dir, monkeypatch):
        """체크 실행 중 예외 발생 시 FAIL을 반환한다."""

        class BrokenCheck(HealthCheckItem):
            name = "broken"
            key = "broken"

            def check(self, ctx):
                raise RuntimeError("test error")

        import healthcheck as hc
        original_all = hc.ALL_CHECKS
        original_map = hc.CHECK_MAP
        try:
            hc.ALL_CHECKS = [BrokenCheck()]
            hc.CHECK_MAP = {c.key: c for c in hc.ALL_CHECKS}
            results = hc.run_healthcheck(str(tmp_plugin_dir))
            assert len(results) == 1
            assert results[0][2] == "FAIL"
            assert "예외" in results[0][3]
        finally:
            hc.ALL_CHECKS = original_all
            hc.CHECK_MAP = original_map


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

    def test_format_text_alignment(self):
        """모든 status 태그가 동일한 너비로 정렬된다."""
        results = [
            ("a", "A", "OK", "ok"),
            ("b", "B", "WARN", "warn"),
            ("c", "C", "FAIL", "fail"),
            ("d", "D", "SKIP", "skip"),
        ]
        output = format_text(results)
        lines = [l for l in output.split("\n") if l.startswith("[")]
        # 모든 태그 뒤 공백 포함하여 동일한 위치에 이름 시작
        name_positions = [l.index("]") + 1 for l in lines]
        # ljust(7)로 태그 폭 통일: [OK]__ = 7, [WARN]_ = 7, [FAIL]_ = 7, [SKIP]_ = 7
        for line in lines:
            # 태그 부분이 7자
            assert len(line.split(" ")[0]) <= 7

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
        assert "진단 항목 없음" in output


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
