#!/usr/bin/env python3
"""PreToolUse hook: matplotlib/weasyprint 직접 사용을 차단하고 내장 스크립트 사용을 강제합니다.

Smart Daily Briefing 플러그인의 차트/PDF 생성 시 한글 폰트가 깨지는 문제를 방지하기 위해,
에이전트가 직접 matplotlib/weasyprint 코드를 작성하거나 실행하는 것을 차단합니다.
반드시 플러그인 내장 스크립트(generate-charts.py, generate-pdf.py)를 사용하도록 강제합니다.
"""
import json
import os
import re
import subprocess
import sys


def find_plugin_script(script_name):
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
                    "-path", f"*/smart-daily-briefing/scripts/{script_name}",
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


def deny(reason):
    """도구 호출을 차단하고 이유를 반환합니다."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(output, sys.stdout)
    sys.exit(0)


def check_bash(tool_input):
    """Bash 명령에서 직접 matplotlib/weasyprint 사용을 감지합니다."""
    command = tool_input.get("command", "")

    # matplotlib 패턴 검사
    if re.search(r"(import\s+matplotlib|from\s+matplotlib|plt\.)", command):
        if "generate-charts.py" in command:
            return  # 내장 스크립트 실행은 허용
        script = find_plugin_script("generate-charts.py")
        deny(
            "직접 matplotlib 코드 실행이 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "반드시 내장 스크립트를 사용하세요:\n"
            'CHART_SCRIPT=$({ find ~/.claude ~/Library/Application\\ Support/Claude '
            '-path "*/smart-daily-briefing/scripts/generate-charts.py" 2>/dev/null; } | head -1)\n'
            'python3 "$CHART_SCRIPT" --input {데이터JSON} --output-dir {출력디렉토리}/ --format auto'
            + (f"\n\n현재 스크립트 위치: {script}" if script else "")
        )

    # weasyprint 패턴 검사
    if re.search(r"(import\s+weasyprint|from\s+weasyprint|HTML\(string=)", command):
        if "generate-pdf.py" in command:
            return  # 내장 스크립트 실행은 허용
        script = find_plugin_script("generate-pdf.py")
        deny(
            "직접 weasyprint 코드 실행이 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "반드시 내장 스크립트를 사용하세요:\n"
            'PDF_SCRIPT=$({ find ~/.claude ~/Library/Application\\ Support/Claude '
            '-path "*/smart-daily-briefing/scripts/generate-pdf.py" 2>/dev/null; } | head -1)\n'
            'python3 "$PDF_SCRIPT" --input {마크다운파일} --output {PDF경로}'
            + (f"\n\n현재 스크립트 위치: {script}" if script else "")
        )


def check_write(tool_input):
    """Write 도구로 matplotlib/weasyprint 포함 Python 파일 작성을 감지합니다."""
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if not file_path.endswith(".py"):
        return

    # 플러그인 내장 스크립트 수정은 허용
    if "smart-daily-briefing/scripts/" in file_path:
        return

    # matplotlib 검사
    if re.search(r"(import\s+matplotlib|from\s+matplotlib)", content):
        script = find_plugin_script("generate-charts.py")
        deny(
            "matplotlib이 포함된 Python 파일 작성이 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "차트 코드를 직접 작성하지 마세요. 반드시 내장 스크립트를 사용하세요:\n"
            'CHART_SCRIPT=$({ find ~/.claude ~/Library/Application\\ Support/Claude '
            '-path "*/smart-daily-briefing/scripts/generate-charts.py" 2>/dev/null; } | head -1)\n'
            'python3 "$CHART_SCRIPT" --input {데이터JSON} --output-dir {출력디렉토리}/ --format auto'
            + (f"\n\n현재 스크립트 위치: {script}" if script else "")
        )

    # weasyprint 검사
    if re.search(r"(import\s+weasyprint|from\s+weasyprint)", content):
        script = find_plugin_script("generate-pdf.py")
        deny(
            "weasyprint이 포함된 Python 파일 작성이 차단되었습니다 (한글 폰트 깨짐 방지).\n\n"
            "PDF 코드를 직접 작성하지 마세요. 반드시 내장 스크립트를 사용하세요:\n"
            'PDF_SCRIPT=$({ find ~/.claude ~/Library/Application\\ Support/Claude '
            '-path "*/smart-daily-briefing/scripts/generate-pdf.py" 2>/dev/null; } | head -1)\n'
            'python3 "$PDF_SCRIPT" --input {마크다운파일} --output {PDF경로}'
            + (f"\n\n현재 스크립트 위치: {script}" if script else "")
        )


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name == "Bash":
        check_bash(tool_input)
    elif tool_name == "Write":
        check_write(tool_input)

    # 기본: 허용
    sys.exit(0)


if __name__ == "__main__":
    main()
