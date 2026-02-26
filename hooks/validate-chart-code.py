#!/usr/bin/env python3
"""PreToolUse hook: matplotlib/weasyprint/PIL 직접 사용을 차단하고 내장 스크립트 사용을 강제합니다.

Smart Daily Briefing 플러그인의 차트/PDF 생성 시 한글 폰트가 깨지는 문제를 방지하기 위해,
에이전트가 직접 matplotlib/weasyprint/PIL 코드를 작성하거나 실행하는 것을 차단합니다.
반드시 플러그인 내장 스크립트(generate-charts.py, generate-pdf.py)를 사용하도록 강제합니다.

검증 방식: AST 기반 화이트리스트 (regex denylist 대신)
- ast.NodeVisitor를 사용하여 import/call 노드를 순회
- 차단 대상 라이브러리의 모든 import 패턴을 탐지
- __import__, importlib.import_module, eval, exec 등 우회 패턴도 탐지
- 인코딩된 바이트 리터럴을 통한 우회도 탐지
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# 차단 대상 라이브러리 목록 (화이트리스트 방식: 이 목록에 있으면 차단)
# ---------------------------------------------------------------------------
BLOCKED_LIBRARIES = {
    # matplotlib 관련
    "matplotlib", "mpl_toolkits", "pylab",
    # weasyprint 관련
    "weasyprint",
    # PIL/Pillow 관련
    "PIL", "Pillow", "pillow",
}

# 차단 라이브러리별 안내 메시지를 위한 카테고리 분류
LIBRARY_CATEGORY = {
    "matplotlib": "chart",
    "mpl_toolkits": "chart",
    "pylab": "chart",
    "weasyprint": "pdf",
    "PIL": "image",
    "Pillow": "image",
    "pillow": "image",
}

# 내장 스크립트 실행 시 허용할 패턴 (Bash 명령에서)
ALLOWED_SCRIPT_PATTERNS = [
    "generate-charts.py",
    "generate-pdf.py",
]


# ---------------------------------------------------------------------------
# AST 기반 코드 검증기
# ---------------------------------------------------------------------------
class ChartCodeValidator(ast.NodeVisitor):
    """AST를 순회하며 차단 대상 라이브러리 사용을 탐지합니다.

    탐지 대상:
    1. import matplotlib / import matplotlib.pyplot as plt
    2. from matplotlib import pyplot
    3. __import__('matplotlib')
    4. importlib.import_module('matplotlib')
    5. eval("import matplotlib") / exec("import matplotlib")
    6. b'\\x69\\x6d\\x70\\x6f\\x72\\x74' 같은 인코딩된 바이트 리터럴
    """

    def __init__(self):
        # 탐지된 위반 사항 목록: (라인번호, 설명, 카테고리)
        self.violations = []

    def _get_top_module(self, module_name: str) -> str | None:
        """모듈 경로에서 최상위 패키지를 추출합니다.

        예: 'matplotlib.pyplot' -> 'matplotlib'
        """
        if not module_name:
            return None
        return module_name.split(".")[0]

    def _check_module_blocked(self, module_name: str, lineno: int, desc: str):
        """모듈 이름이 차단 목록에 있는지 확인합니다."""
        top = self._get_top_module(module_name)
        if top and top in BLOCKED_LIBRARIES:
            category = LIBRARY_CATEGORY.get(top, "unknown")
            self.violations.append((lineno, f"{desc}: {module_name}", category))

    # ----- import 문 처리 -----

    def visit_Import(self, node: ast.Import):
        """'import matplotlib' / 'import matplotlib.pyplot as plt' 탐지"""
        for alias in node.names:
            self._check_module_blocked(alias.name, node.lineno, "import 문")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """'from matplotlib import pyplot' / 'from PIL import Image' 탐지"""
        if node.module:
            self._check_module_blocked(node.module, node.lineno, "from-import 문")
        self.generic_visit(node)

    # ----- 함수 호출을 통한 동적 import 탐지 -----

    def visit_Call(self, node: ast.Call):
        """동적 import 패턴을 탐지합니다.

        - __import__('matplotlib')
        - importlib.import_module('matplotlib')
        - eval("import matplotlib") / exec("import matplotlib")
        """
        func = node.func

        # __import__('matplotlib') 패턴
        if isinstance(func, ast.Name) and func.id == "__import__":
            self._check_call_args_for_blocked(node, "__import__() 호출")

        # importlib.import_module('matplotlib') 패턴
        elif isinstance(func, ast.Attribute) and func.attr == "import_module":
            # importlib.import_module 또는 어떤 객체.import_module이든 탐지
            self._check_call_args_for_blocked(node, "import_module() 호출")

        # eval("import matplotlib") / exec("import matplotlib") 패턴
        elif isinstance(func, ast.Name) and func.id in ("eval", "exec"):
            self._check_eval_exec_args(node, func.id)

        self.generic_visit(node)

    def _check_call_args_for_blocked(self, node: ast.Call, desc: str):
        """함수 호출의 첫 번째 인자에서 차단 대상 라이브러리명을 확인합니다."""
        if node.args:
            arg = node.args[0]
            # 문자열 리터럴인 경우
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                module_name = arg.value.strip()
                self._check_module_blocked(module_name, node.lineno, desc)
            # JoinedStr(f-string)인 경우에도 정적 부분 검사
            elif isinstance(arg, ast.JoinedStr):
                static_parts = "".join(
                    v.value for v in arg.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                )
                for lib in BLOCKED_LIBRARIES:
                    if lib in static_parts:
                        category = LIBRARY_CATEGORY.get(lib, "unknown")
                        self.violations.append(
                            (node.lineno, f"{desc} (f-string): {lib}", category)
                        )

    def _check_eval_exec_args(self, node: ast.Call, func_name: str):
        """eval/exec 인자 문자열에서 import 문을 탐지합니다."""
        if not node.args:
            return
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            code_str = arg.value
            for lib in BLOCKED_LIBRARIES:
                if lib in code_str:
                    category = LIBRARY_CATEGORY.get(lib, "unknown")
                    self.violations.append(
                        (node.lineno, f"{func_name}() 내 {lib} 참조", category)
                    )

    # ----- 바이트 리터럴을 통한 우회 탐지 -----

    def visit_Constant(self, node: ast.Constant):
        """인코딩된 바이트 리터럴에서 차단 대상 라이브러리명을 탐지합니다.

        예: b'\\x69\\x6d\\x70\\x6f\\x72\\x74' (= b'import')
        """
        if isinstance(node.value, bytes):
            try:
                decoded = node.value.decode("utf-8", errors="ignore")
            except Exception:
                decoded = ""
            for lib in BLOCKED_LIBRARIES:
                if lib in decoded:
                    category = LIBRARY_CATEGORY.get(lib, "unknown")
                    self.violations.append(
                        (node.lineno, f"바이트 리터럴 내 {lib} 참조", category)
                    )
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# 텍스트 기반 추가 검증 (AST 파싱 실패 시 또는 비-Python 코드 대비)
# ---------------------------------------------------------------------------
def text_fallback_check(code: str) -> list[tuple[int, str, str]]:
    """AST 파싱이 불가능한 경우 텍스트 기반으로 차단 대상을 탐지합니다.

    Bash 명령어 내 python -c "..." 패턴이나
    코드 조각이 완전한 Python이 아닌 경우에 대비합니다.
    """
    violations = []
    for i, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        for lib in BLOCKED_LIBRARIES:
            # import 문 패턴 (공백/탭 이후)
            if re.search(rf'\bimport\s+{re.escape(lib)}\b', stripped):
                category = LIBRARY_CATEGORY.get(lib, "unknown")
                violations.append((i, f"텍스트 탐지 - import {lib}", category))
            elif re.search(rf'\bfrom\s+{re.escape(lib)}\b', stripped):
                category = LIBRARY_CATEGORY.get(lib, "unknown")
                violations.append((i, f"텍스트 탐지 - from {lib}", category))
            # __import__ 패턴
            elif re.search(rf"__import__\s*\(\s*['\"]" + re.escape(lib), stripped):
                category = LIBRARY_CATEGORY.get(lib, "unknown")
                violations.append((i, f"텍스트 탐지 - __import__('{lib}')", category))
            # import_module 패턴
            elif re.search(rf"import_module\s*\(\s*['\"]" + re.escape(lib), stripped):
                category = LIBRARY_CATEGORY.get(lib, "unknown")
                violations.append(
                    (i, f"텍스트 탐지 - import_module('{lib}')", category)
                )
    return violations


def validate_python_code(code: str) -> list[tuple[int, str, str]]:
    """Python 코드를 AST로 파싱하여 검증합니다. 실패 시 텍스트 폴백을 사용합니다."""
    try:
        tree = ast.parse(code)
        validator = ChartCodeValidator()
        validator.visit(tree)
        return validator.violations
    except SyntaxError:
        # AST 파싱 실패 시 텍스트 기반 폴백
        return text_fallback_check(code)


# ---------------------------------------------------------------------------
# 유틸리티 함수들
# ---------------------------------------------------------------------------
def find_plugin_script(script_name: str) -> str | None:
    """플러그인 설치 위치에서 스크립트를 찾습니다."""
    search_dirs = [
        os.path.expanduser("~/.claude"),
        os.path.expanduser("~/Library/Application Support/Claude"),
    ]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        try:
            result = subprocess.run(
                [
                    "find", d,
                    "-name", script_name, "-path", "*smart-daily-briefing*",
                    "-type", "f",
                ],
                capture_output=True, text=True, timeout=5,
            )
            paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            if paths:
                return paths[0]
        except Exception:
            continue
    return None


def deny(reason: str):
    """도구 호출을 차단하고 이유를 반환합니다. (exit 2 + JSON 출력)"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(output, sys.stdout)
    sys.exit(2)


def build_deny_message(violations: list[tuple[int, str, str]]) -> str:
    """위반 사항 목록으로부터 차단 메시지를 생성합니다."""
    # 위반 카테고리 수집
    categories = {v[2] for v in violations}

    parts = []
    violation_details = "\n".join(f"  - Line {v[0]}: {v[1]}" for v in violations)

    if "chart" in categories:
        script = find_plugin_script("generate-charts.py")
        parts.append(
            "matplotlib/pylab이 포함된 코드가 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "반드시 내장 스크립트를 사용하세요:\n"
            'CHART_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-charts.py"\n'
            'python3 "$CHART_SCRIPT" --input {데이터JSON} --output-dir {출력디렉토리}/ --format auto\n'
            "($SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정합니다)"
            + (f"\n현재 스크립트 위치: {script}" if script else "")
        )

    if "pdf" in categories:
        script = find_plugin_script("generate-pdf.py")
        parts.append(
            "weasyprint이 포함된 코드가 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "반드시 내장 스크립트를 사용하세요:\n"
            'PDF_SCRIPT="${SMART_BRIEFING_ROOT}/scripts/generate-pdf.py"\n'
            'python3 "$PDF_SCRIPT" --input {마크다운파일} --output {PDF경로}\n'
            "($SMART_BRIEFING_ROOT는 SessionStart 훅이 자동 설정합니다)"
            + (f"\n현재 스크립트 위치: {script}" if script else "")
        )

    if "image" in categories:
        parts.append(
            "PIL/Pillow가 포함된 코드가 차단되었습니다.\n"
            "이미지 처리가 필요한 경우 내장 스크립트를 사용하세요."
        )

    header = "차단된 코드 패턴이 감지되었습니다:\n" + violation_details + "\n\n"
    return header + "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Bash / Write 도구별 검증 로직
# ---------------------------------------------------------------------------
def extract_python_from_bash(command: str) -> str | None:
    """Bash 명령어에서 인라인 Python 코드를 추출합니다.

    python -c "...", python3 -c '...', python3 << 'EOF' ... EOF 등의 패턴을 처리합니다.
    """
    # python -c "code" / python3 -c 'code' 패턴
    # 경로 포함(/usr/bin/python3), 버전 포함(python3.12) 매칭 지원
    match = re.search(
        r'''(?:^|/|\s)python[3]?(?:\.\d+)?\s+-c\s+(['"])(.*?)\1''',
        command,
        re.DOTALL,
    )
    if match:
        return match.group(2)

    # heredoc 패턴: python3 << 'EOF' ... EOF
    match = re.search(
        r"""(?:^|/|\s)python[3]?(?:\.\d+)?\s+<<\s*['"]?(\w+)['"]?\s*\n(.*?)\n\1""",
        command,
        re.DOTALL,
    )
    if match:
        return match.group(2)

    return None


def check_bash(tool_input: dict):
    """Bash 명령에서 차단 대상 라이브러리 사용을 검증합니다."""
    command = tool_input.get("command", "")
    if not command:
        return

    # 내장 스크립트 실행은 허용 (단일 명령어가 스크립트를 직접 실행하는 경우만)
    # bash 주석(#) 이후 제거, 복합 명령(;, &&, ||)은 허용하지 않음
    cmd_effective = re.split(r'(?<!\S)#', command.strip(), maxsplit=1)[0].strip()
    if not re.search(r'[;&|]', cmd_effective):
        for pattern in ALLOWED_SCRIPT_PATTERNS:
            if pattern in cmd_effective:
                return

    # 1) 전체 명령어를 텍스트 기반으로 먼저 검사 (빠른 경로)
    all_violations = text_fallback_check(command)

    # 2) 인라인 Python 코드가 있으면 AST 기반으로 정밀 검사
    inline_python = extract_python_from_bash(command)
    if inline_python:
        ast_violations = validate_python_code(inline_python)
        # 중복 제거를 위해 설명 기반으로 합침
        existing_descs = {v[1] for v in all_violations}
        for v in ast_violations:
            if v[1] not in existing_descs:
                all_violations.append(v)

    if all_violations:
        deny(build_deny_message(all_violations))


def check_write(tool_input: dict):
    """Write 도구로 차단 대상 라이브러리가 포함된 파일 작성을 검증합니다."""
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if not content:
        return

    # 플러그인 내장 스크립트 수정은 허용
    # normpath로 .. 경로 정규화 후, 프로젝트 scripts/ 디렉토리 패턴 확인
    norm_path = os.path.normpath(file_path)
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_scripts_dir = os.path.normpath(os.path.join(os.path.dirname(hook_dir), "scripts"))
    # 현재 프로젝트 또는 다른 설치 위치의 scripts/ 디렉토리 허용
    if norm_path.startswith(plugin_scripts_dir + os.sep) or \
       "/smart-daily-briefing/scripts/" in norm_path:
        return

    # Python 파일인 경우 AST 기반 정밀 검사
    if file_path.endswith(".py"):
        violations = validate_python_code(content)
    else:
        # Python 파일이 아니어도 텍스트 기반으로 검사 (셸 스크립트 등)
        violations = text_fallback_check(content)

    if violations:
        deny(build_deny_message(violations))


# ---------------------------------------------------------------------------
# 메인 엔트리포인트
# ---------------------------------------------------------------------------
def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # 입력 파싱 실패 시 stderr 경고 후 허용 (fail-open)
        # NOTE: fail-closed(exit 2)가 더 안전하나, 훅 프레임워크와의 호환성을 위해 허용 유지
        print("WARNING: validate-chart-code hook received invalid JSON input", file=sys.stderr)
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name == "Bash":
        check_bash(tool_input)
    elif tool_name == "Write":
        check_write(tool_input)

    # 기본: 허용 (exit 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
