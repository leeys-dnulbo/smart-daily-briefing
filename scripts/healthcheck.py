#!/usr/bin/env python3
"""
Smart Daily Briefing - 환경 진단 (헬스체크)

시스템 구성 요소의 상태를 점검합니다.
독립 실행 가능 + 모듈 import 가능한 이중 구조.

Usage:
    python3 scripts/healthcheck.py              # 전체 진단
    python3 scripts/healthcheck.py --json       # JSON 출력
    python3 scripts/healthcheck.py --check mcp  # 특정 항목만

Exit codes:
    0 = all OK
    1 = warning exists
    2 = fail exists
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta


# ---------- 헬스체크 항목 인터페이스 ----------

class HealthCheckItem:
    """v2.0.0에서 Telegram/Discord 등 새 항목 추가 시 이 클래스를 상속.

    Attributes:
        name: 진단 항목 이름 (한국어)
        key: 프로그래밍용 키 (영문)
    """
    name: str = ""
    key: str = ""

    def check(self, ctx):
        """진단 실행.

        Args:
            ctx: dict — 공유 컨텍스트 (plugin_dir 등)

        Returns:
            (status, message): status는 "OK", "WARN", "FAIL", "SKIP" 중 하나.
        """
        raise NotImplementedError


# ---------- 개별 진단 항목 ----------

class ConfigCheck(HealthCheckItem):
    name = "config.json"
    key = "config"

    def check(self, ctx):
        config_path = os.path.join(ctx["plugin_dir"], "config.json")
        if not os.path.exists(config_path):
            return "WARN", "config.json 없음 (기본 설정 사용)"
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("version", "?")
            preset = data.get("preset", "?")
            return "OK", f"유효 (v{version}, preset={preset})"
        except (json.JSONDecodeError, OSError) as e:
            return "FAIL", f"파싱 실패: {e}"


class PythonEnvCheck(HealthCheckItem):
    name = "Python 환경"
    key = "python"

    def check(self, ctx):
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        exe = sys.executable
        if "/opt/homebrew/" in exe or "/usr/local/Cellar/" in exe:
            source = "homebrew"
        elif "virtualenv" in exe or "venv" in exe or ".venv" in exe:
            source = "venv"
        elif "conda" in exe:
            source = "conda"
        else:
            source = "system"
        if sys.version_info < (3, 9):
            return "WARN", f"{version} ({source}) — 3.9 이상 권장"
        return "OK", f"{version} ({source})"


class MatplotlibCheck(HealthCheckItem):
    name = "matplotlib"
    key = "matplotlib"

    def check(self, ctx):
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import matplotlib; print(matplotlib.__version__)"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                ver = result.stdout.strip()
                return "OK", f"설치됨 (v{ver})"
            return "WARN", "미설치 (SVG fallback 사용)"
        except (OSError, subprocess.TimeoutExpired):
            return "WARN", "확인 불가"


class WeasyprintCheck(HealthCheckItem):
    name = "weasyprint"
    key = "weasyprint"

    def check(self, ctx):
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import weasyprint; print(weasyprint.__version__)"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                ver = result.stdout.strip()
                return "OK", f"설치됨 (v{ver})"
            return "WARN", "미설치 (PDF 생성 불가)"
        except (OSError, subprocess.TimeoutExpired):
            return "WARN", "확인 불가"


class SlackCheck(HealthCheckItem):
    name = "Slack webhook"
    key = "slack"

    def check(self, ctx):
        config_path = os.path.join(ctx["plugin_dir"], "config.json")
        if not os.path.exists(config_path):
            return "SKIP", "config.json 없음"
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return "FAIL", "config.json 파싱 실패"

        slack = data.get("notifications", {}).get("slack", {})
        url = slack.get("webhook_url", "")
        if not url:
            return "SKIP", "webhook URL 미설정"
        if not url.startswith("https://"):
            return "FAIL", "webhook URL은 https://로 시작해야 합니다"

        # HEAD 요청으로 연결 테스트
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status < 500:
                    return "OK", "연결됨"
                return "FAIL", f"서버 에러 (HTTP {resp.status})"
        except Exception as e:
            return "WARN", f"연결 테스트 실패: {type(e).__name__}"


class SidecarCheck(HealthCheckItem):
    name = "sidecar 파일"
    key = "sidecar"

    def check(self, ctx):
        briefings_dir = os.path.join(ctx["plugin_dir"], "briefings")
        if not os.path.isdir(briefings_dir):
            return "WARN", "briefings/ 디렉토리 없음"

        today = datetime.now()
        count = 0
        for i in range(7):
            d = today - timedelta(days=i + 1)
            path = os.path.join(briefings_dir, f"{d.strftime('%Y-%m-%d')}.json")
            if os.path.exists(path):
                count += 1

        if count >= 5:
            return "OK", f"최근 7일 중 {count}일 존재"
        elif count > 0:
            return "WARN", f"최근 7일 중 {count}일만 존재 (주간 요약에 부족할 수 있음)"
        else:
            return "WARN", "최근 7일 sidecar 없음"


class FontCheck(HealthCheckItem):
    name = "한국어 폰트"
    key = "font"

    def check(self, ctx):
        scripts_dir = os.path.join(ctx["plugin_dir"], "scripts")
        utils_path = os.path.join(scripts_dir, "utils.py")
        if not os.path.exists(utils_path):
            return "WARN", "utils.py 파일 없음"
        try:
            spec = importlib.util.spec_from_file_location("_healthcheck_utils", utils_path)
            utils_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(utils_mod)
            font_path = utils_mod.find_korean_font()
            if font_path:
                name = os.path.basename(font_path)
                return "OK", f"{name}"
            return "WARN", "한국어 폰트를 찾을 수 없음 (차트 한글 깨짐 가능)"
        except (ImportError, AttributeError):
            return "WARN", "utils.py import 실패"
        except Exception as e:
            return "WARN", f"폰트 확인 실패: {type(e).__name__}"


class ScriptsCheck(HealthCheckItem):
    name = "필수 스크립트"
    key = "scripts"

    def check(self, ctx):
        scripts_dir = os.path.join(ctx["plugin_dir"], "scripts")
        required = ["generate-charts.py", "generate-pdf.py", "manage-schedule.sh", "send-slack.sh"]
        missing = [s for s in required if not os.path.exists(os.path.join(scripts_dir, s))]
        if not missing:
            return "OK", f"{len(required)}개 모두 존재"
        return "FAIL", f"누락: {', '.join(missing)}"


# ---------- 헬스체크 실행기 ----------

ALL_CHECKS = [
    ConfigCheck(),
    PythonEnvCheck(),
    MatplotlibCheck(),
    WeasyprintCheck(),
    SlackCheck(),
    SidecarCheck(),
    FontCheck(),
    ScriptsCheck(),
]

CHECK_MAP = {c.key: c for c in ALL_CHECKS}


def run_healthcheck(plugin_dir, checks=None):
    """헬스체크를 실행한다.

    Args:
        plugin_dir: 플러그인 루트 디렉토리
        checks: 실행할 체크 키 목록 (None이면 전체)

    Returns:
        list of (key, name, status, message) 튜플
    """
    ctx = {"plugin_dir": plugin_dir}
    if checks is not None:
        items = []
        for k in checks:
            if k in CHECK_MAP:
                items.append(CHECK_MAP[k])
            else:
                # 알 수 없는 키는 FAIL로 기록
                items.append(None)
    else:
        items = list(ALL_CHECKS)

    results = []
    for i, item in enumerate(items):
        if item is None:
            key = checks[i] if checks else "unknown"
            results.append((key, key, "FAIL", f"알 수 없는 진단 항목: {key}"))
            continue
        try:
            status, message = item.check(ctx)
        except Exception as e:
            status, message = "FAIL", f"예외 발생: {e}"
        results.append((item.key, item.name, status, message))
    return results


def format_text(results):
    """결과를 터미널 텍스트로 포맷."""
    lines = ["Smart Daily Briefing — 환경 진단", ""]
    for key, name, status, message in results:
        tag = f"[{status}]".ljust(7)
        lines.append(f"{tag} {name}: {message}")

    ok_count = sum(1 for _, _, s, _ in results if s == "OK")
    warn_count = sum(1 for _, _, s, _ in results if s == "WARN")
    fail_count = sum(1 for _, _, s, _ in results if s == "FAIL")
    skip_count = sum(1 for _, _, s, _ in results if s == "SKIP")

    parts = []
    if ok_count: parts.append(f"{ok_count} 정상")
    if warn_count: parts.append(f"{warn_count} 경고")
    if fail_count: parts.append(f"{fail_count} 실패")
    if skip_count: parts.append(f"{skip_count} 건너뜀")

    lines.append("")
    if parts:
        lines.append(f"결과: {', '.join(parts)}")
    else:
        lines.append("결과: 진단 항목 없음")
    return "\n".join(lines)


def format_json(results):
    """결과를 JSON으로 포맷."""
    items = {}
    for key, name, status, message in results:
        items[key] = {"name": name, "status": status, "message": message}
    return json.dumps(items, ensure_ascii=False, indent=2)


def get_exit_code(results):
    """결과에 따른 종료 코드 반환."""
    statuses = {s for _, _, s, _ in results}
    if "FAIL" in statuses:
        return 2
    if "WARN" in statuses:
        return 1
    return 0


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Smart Daily Briefing 환경 진단")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--check", type=str, help="특정 항목만 진단 (쉼표 구분)")
    parser.add_argument("--plugin-dir", type=str, help="플러그인 디렉토리 경로")
    args = parser.parse_args()

    plugin_dir = args.plugin_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    checks = [k.strip() for k in args.check.split(",")] if args.check else None

    results = run_healthcheck(plugin_dir, checks)

    if args.json:
        print(format_json(results))
    else:
        print(format_text(results))

    sys.exit(get_exit_code(results))


if __name__ == "__main__":
    main()
