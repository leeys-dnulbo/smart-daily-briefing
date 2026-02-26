"""Smart Daily Briefing - 테스트 설정"""

import importlib.util
import json
import os
import sys

import pytest

# scripts/ 디렉토리를 Python path에 추가
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

# hooks/ 디렉토리를 Python path에 추가
HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
sys.path.insert(0, HOOKS_DIR)

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# 하이픈 모듈 로더
# ---------------------------------------------------------------------------

def _load_hyphenated_module(module_name, file_name):
    """scripts/ 아래 하이픈 포함 .py 파일을 단일 모듈 객체로 로드."""
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(SCRIPTS_DIR, file_name),
        )
        if spec is None:
            raise ImportError(f"{file_name} not found in {SCRIPTS_DIR}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[module_name]

_load_hyphenated_module("send_notification", "send-notification.py")


# ---------------------------------------------------------------------------
# 공유 fixture: send_notification 모듈의 전역 변수를 임시 디렉토리로 패치
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_plugin_dir(tmp_path, monkeypatch):
    """임시 플러그인 디렉토리를 생성하고 send_notification 모듈 전역 변수를 패치."""
    briefings_dir = tmp_path / "briefings"
    briefings_dir.mkdir()
    config_path = tmp_path / "config.json"

    import send_notification as mod

    monkeypatch.setattr(mod, "PLUGIN_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(mod, "QUEUE_PATH", str(briefings_dir / "notification-queue.json"))
    monkeypatch.setattr(mod, "LOG_PATH", str(briefings_dir / "schedule.log"))
    return tmp_path
