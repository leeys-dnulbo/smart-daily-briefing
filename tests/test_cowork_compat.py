"""tests/test_cowork_compat.py — Cowork(Claude Desktop) 호환성 테스트"""

import os
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from unittest.mock import MagicMock

import pytest

# conftest.py에서 scripts/ 경로가 추가됨
import utils
from healthcheck import ProxyCheck


# ---------- ProxyCheck 테스트 ----------


class TestProxyCheck:
    def test_skip_on_macos(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        status, msg = ProxyCheck().check({"plugin_dir": "."})
        assert status == "SKIP"
        assert "macOS" in msg

    def test_warn_no_proxy_in_container(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.delenv("http_proxy", raising=False)
        monkeypatch.delenv("https_proxy", raising=False)
        original_exists = os.path.exists
        monkeypatch.setattr(os.path, "exists", lambda p: False if p == "/run/systemd/system" else original_exists(p))
        status, msg = ProxyCheck().check({"plugin_dir": "."})
        assert status == "WARN"
        assert "컨테이너" in msg

    def test_skip_regular_linux_no_proxy(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.delenv("http_proxy", raising=False)
        monkeypatch.delenv("https_proxy", raising=False)
        # /run/systemd/system exists → regular Linux
        original_exists = os.path.exists
        monkeypatch.setattr(os.path, "exists", lambda p: True if p == "/run/systemd/system" else original_exists(p))
        status, msg = ProxyCheck().check({"plugin_dir": "."})
        assert status == "SKIP"
        assert "일반 Linux" in msg

    def test_ok_with_working_proxy(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy:3128")

        class MockResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self): return b""

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: MockResp())
        status, msg = ProxyCheck().check({"plugin_dir": "."})
        assert status == "OK"
        assert "프록시 연결됨" in msg

    def test_fail_with_broken_proxy(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy:3128")

        def raise_error(*a, **kw):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", raise_error)
        status, msg = ProxyCheck().check({"plugin_dir": "."})
        assert status == "FAIL"
        assert "연결 실패" in msg


# ---------- utils.py 플랫폼 가드 테스트 ----------


class TestUtilsPlatformGuard:
    def test_homebrew_pythons_is_list(self):
        """_HOMEBREW_PYTHONS는 항상 리스트이다."""
        assert isinstance(utils._HOMEBREW_PYTHONS, list)

    def test_homebrew_pythons_conditional_on_platform(self):
        """macOS가 아닌 플랫폼에서는 _HOMEBREW_PYTHONS가 비어있어야 한다."""
        if platform.system() != "Darwin":
            assert utils._HOMEBREW_PYTHONS == []
        else:
            assert len(utils._HOMEBREW_PYTHONS) > 0

    def test_is_macos_flag(self):
        """_IS_MACOS는 현재 플랫폼과 일치해야 한다."""
        assert utils._IS_MACOS == (platform.system() == "Darwin")

    def test_other_pythons_always_populated(self):
        """_OTHER_PYTHONS는 플랫폼에 관계없이 항상 있다."""
        assert len(utils._OTHER_PYTHONS) >= 2


class TestEnsureBestPython:
    def test_skips_reexec_when_import_works(self, monkeypatch):
        """현재 Python이 import 가능하면 reexec하지 않는다."""
        calls = []
        monkeypatch.setattr(utils, "reexec_with_better_python", lambda x: calls.append(x))
        # _IS_MACOS=False로 설정하여 Linux 경로 테스트
        monkeypatch.setattr(utils, "_IS_MACOS", False)
        # subprocess.run이 성공 반환
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: MagicMock(returncode=0)
        )
        utils.ensure_best_python("import json")
        assert len(calls) == 0

    def test_calls_reexec_when_import_fails(self, monkeypatch):
        """현재 Python이 import 실패하면 reexec을 시도한다."""
        calls = []
        monkeypatch.setattr(utils, "reexec_with_better_python", lambda x: calls.append(x))
        monkeypatch.setattr(utils, "_IS_MACOS", False)
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: MagicMock(returncode=1)
        )
        utils.ensure_best_python("import nonexistent_module")
        assert len(calls) == 1

    def test_macos_non_homebrew_calls_reexec(self, monkeypatch):
        """macOS에서 Homebrew Python이 아니면 reexec을 시도한다."""
        calls = []
        monkeypatch.setattr(utils, "reexec_with_better_python", lambda x: calls.append(x))
        monkeypatch.setattr(utils, "_IS_MACOS", True)
        monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
        utils.ensure_best_python("import json")
        assert len(calls) == 1

    def test_macos_homebrew_skips_when_import_works(self, monkeypatch):
        """macOS Homebrew Python에서 import 성공하면 reexec하지 않는다."""
        calls = []
        monkeypatch.setattr(utils, "reexec_with_better_python", lambda x: calls.append(x))
        monkeypatch.setattr(utils, "_IS_MACOS", True)
        monkeypatch.setattr(sys, "executable", "/opt/homebrew/bin/python3.12")
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: MagicMock(returncode=0)
        )
        utils.ensure_best_python("import json")
        assert len(calls) == 0
