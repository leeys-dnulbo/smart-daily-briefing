"""scripts/utils.py 단위 테스트"""

import json
import os
import tempfile

import pytest

from utils import (
    auto_install,
    find_korean_font,
    get_font_family_name,
    get_mono_family_name,
    safe_write,
    safe_write_json,
    FONT_SEARCH_PATHS,
)


class TestSafeWrite:
    """safe_write / safe_write_json 테스트"""

    def test_safe_write_creates_file(self, tmp_path):
        path = str(tmp_path / "test.txt")
        safe_write(path, "hello world")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            assert f.read() == "hello world"

    def test_safe_write_overwrites_existing(self, tmp_path):
        path = str(tmp_path / "test.txt")
        safe_write(path, "first")
        safe_write(path, "second")
        with open(path, encoding="utf-8") as f:
            assert f.read() == "second"

    def test_safe_write_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "a" / "b" / "c" / "test.txt")
        safe_write(path, "nested")
        assert os.path.exists(path)

    def test_safe_write_unicode(self, tmp_path):
        path = str(tmp_path / "korean.txt")
        content = "한국어 테스트 데이터 🎯"
        safe_write(path, content)
        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_safe_write_json_creates_valid_json(self, tmp_path):
        path = str(tmp_path / "data.json")
        data = {"name": "테스트", "values": [1, 2, 3], "nested": {"key": "value"}}
        safe_write_json(path, data)
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_safe_write_json_no_ascii_escape(self, tmp_path):
        path = str(tmp_path / "korean.json")
        data = {"이름": "홍길동"}
        safe_write_json(path, data)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "홍길동" in content
        assert "\\u" not in content

    def test_safe_write_json_trailing_newline(self, tmp_path):
        path = str(tmp_path / "data.json")
        safe_write_json(path, {"a": 1})
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content.endswith("\n")


class TestFontSearch:
    """폰트 검색 관련 테스트"""

    def test_font_search_paths_has_darwin(self):
        assert "Darwin" in FONT_SEARCH_PATHS

    def test_font_search_paths_has_linux(self):
        assert "Linux" in FONT_SEARCH_PATHS

    def test_get_font_family_name_darwin(self):
        result = get_font_family_name("Darwin")
        assert "Apple" in result
        assert "sans-serif" in result

    def test_get_font_family_name_linux(self):
        result = get_font_family_name("Linux")
        assert "sans-serif" in result

    def test_get_font_family_name_unknown(self):
        result = get_font_family_name("Windows")
        assert result == "sans-serif"

    def test_get_mono_family_name_darwin(self):
        result = get_mono_family_name("Darwin")
        assert "Menlo" in result
        assert "monospace" in result

    def test_get_mono_family_name_linux(self):
        result = get_mono_family_name("Linux")
        assert "monospace" in result

    def test_find_korean_font_returns_path_or_none(self):
        result = find_korean_font()
        if result is not None:
            assert os.path.exists(result)


class TestAutoInstall:
    """auto_install 테스트"""

    def test_auto_install_already_installed(self):
        # json은 표준 라이브러리이므로 항상 설치 가능
        # auto_install은 pip install 시도이므로 이미 설치된 패키지에 대해서도 True 반환
        result = auto_install("pip")
        assert isinstance(result, bool)

    def test_auto_install_nonexistent_package(self):
        result = auto_install("this-package-definitely-does-not-exist-12345")
        assert result is False
