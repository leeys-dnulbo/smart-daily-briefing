"""hooks/validate-chart-code.py AST 검증 테스트"""

import json
import subprocess
import sys
import os

import pytest

# 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_SCRIPT = os.path.join(PROJECT_ROOT, "hooks", "validate-chart-code.py")


def run_hook(tool_name, tool_input):
    """훅 스크립트를 실행하고 결과를 반환"""
    stdin_data = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, HOOK_SCRIPT],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


class TestBashBlocking:
    """Bash 도구에서 차단되어야 하는 패턴들"""

    def _assert_denied(self, result):
        """deny 시 exit code 2 + JSON deny 응답 확인"""
        assert result.returncode == 2
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_blocks_import_matplotlib(self):
        result = run_hook("Bash", {"command": "python3 -c 'import matplotlib'"})
        self._assert_denied(result)

    def test_blocks_from_matplotlib_import(self):
        result = run_hook("Bash", {"command": "python3 -c 'from matplotlib import pyplot'"})
        self._assert_denied(result)

    def test_blocks_import_weasyprint(self):
        result = run_hook("Bash", {"command": "python3 -c 'import weasyprint'"})
        self._assert_denied(result)

    def test_blocks_from_weasyprint(self):
        result = run_hook("Bash", {"command": "python3 -c 'from weasyprint import HTML'"})
        self._assert_denied(result)

    def test_blocks_dunder_import(self):
        result = run_hook("Bash", {"command": "python3 -c \"__import__('matplotlib')\""})
        self._assert_denied(result)

    def test_blocks_import_pil(self):
        result = run_hook("Bash", {"command": "python3 -c 'from PIL import Image'"})
        self._assert_denied(result)


class TestBashAllowing:
    """Bash 도구에서 허용되어야 하는 패턴들"""

    def _assert_allowed(self, result):
        """허용 시 exit code 0 확인"""
        assert result.returncode == 0

    def test_allows_generate_charts_script(self):
        result = run_hook("Bash", {"command": "python3 scripts/generate-charts.py --input data.json --output-dir out/"})
        self._assert_allowed(result)

    def test_allows_generate_pdf_script(self):
        result = run_hook("Bash", {"command": "python3 scripts/generate-pdf.py --input brief.md --output brief.pdf"})
        self._assert_allowed(result)

    def test_allows_normal_python(self):
        result = run_hook("Bash", {"command": "python3 -c 'import json; print(json.dumps({\"a\": 1}))'"})
        self._assert_allowed(result)

    def test_allows_non_python_commands(self):
        result = run_hook("Bash", {"command": "ls -la"})
        self._assert_allowed(result)


class TestWriteBlocking:
    """Write 도구에서 차단되어야 하는 패턴들"""

    def _assert_denied(self, result):
        assert result.returncode == 2
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_blocks_matplotlib_in_py_file(self):
        result = run_hook("Write", {
            "file_path": "/tmp/chart.py",
            "content": "import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nplt.savefig('chart.png')"
        })
        self._assert_denied(result)

    def test_blocks_weasyprint_in_py_file(self):
        result = run_hook("Write", {
            "file_path": "/tmp/pdf_gen.py",
            "content": "from weasyprint import HTML\nHTML(string='<h1>hi</h1>').write_pdf('out.pdf')"
        })
        self._assert_denied(result)


class TestWriteAllowing:
    """Write 도구에서 허용되어야 하는 패턴들"""

    def _assert_allowed(self, result):
        assert result.returncode == 0

    def test_allows_non_py_files(self):
        """비-Python 파일은 텍스트 검사를 하므로 import 문구가 있어도 문맥에 따라 다름.
        일반 문장(import matplotlib is cool)은 허용되어야 함."""
        result = run_hook("Write", {
            "file_path": "/tmp/test.md",
            "content": "matplotlib is a great library for charts"
        })
        self._assert_allowed(result)

    def test_allows_plugin_scripts(self):
        result = run_hook("Write", {
            "file_path": "/home/user/smart-daily-briefing/scripts/generate-charts.py",
            "content": "import matplotlib\nmatplotlib.use('Agg')"
        })
        self._assert_allowed(result)

    def test_allows_clean_python(self):
        result = run_hook("Write", {
            "file_path": "/tmp/clean.py",
            "content": "import json\nimport os\nprint('hello')"
        })
        self._assert_allowed(result)


class TestEdgeCases:
    """엣지 케이스"""

    def test_invalid_json_input(self):
        """잘못된 JSON 입력은 허용 (exit 0)"""
        result = subprocess.run(
            [sys.executable, HOOK_SCRIPT],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_empty_tool_input(self):
        """빈 tool_input은 허용"""
        result = run_hook("Bash", {})
        assert result.returncode == 0

    def test_unknown_tool(self):
        """알 수 없는 도구는 허용"""
        result = run_hook("UnknownTool", {"content": "import matplotlib"})
        assert result.returncode == 0
