#!/usr/bin/env python3
"""
Smart Daily Briefing - 공통 유틸리티

generate-charts.py, generate-pdf.py에서 공유하는 유틸리티 함수:
- Python 자동 전환 (homebrew 우선)
- pip 자동 설치
- 한국어 폰트 탐색
- 안전한 파일 쓰기 (atomic write)
"""

import json
import os
import platform
import subprocess
import sys
import tempfile


# ---------- Python 자동 전환 ----------
_HOMEBREW_PYTHONS = [
    '/opt/homebrew/bin/python3.13',
    '/opt/homebrew/bin/python3.12',
    '/opt/homebrew/bin/python3.11',
]
_OTHER_PYTHONS = [
    '/usr/local/bin/python3',
    '/usr/bin/python3',
]


def reexec_with_better_python(test_import):
    """더 좋은 Python(homebrew 우선)으로 재실행.

    Args:
        test_import: 테스트할 import 문자열 (예: 'import matplotlib', 'from weasyprint import HTML')
    """
    candidates = _HOMEBREW_PYTHONS + _OTHER_PYTHONS
    for py in candidates:
        if py == sys.executable or not os.path.exists(py):
            continue
        try:
            result = subprocess.run(
                [py, '-c', test_import],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                print(f"  Re-exec with: {py}", file=sys.stderr)
                try:
                    os.execv(py, [py] + sys.argv)
                except OSError as e:
                    print(f"  WARNING: os.execv failed for {py}: {e}", file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired):
            continue


def ensure_best_python(test_import):
    """현재 Python이 최적이 아니면 더 좋은 Python으로 재실행을 시도.

    Args:
        test_import: 테스트할 import 문자열
    """
    if '/opt/homebrew/' not in sys.executable:
        reexec_with_better_python(test_import)
    else:
        # exec() 대신 subprocess로 안전하게 import 가능 여부 테스트
        try:
            result = subprocess.run(
                [sys.executable, '-c', test_import],
                capture_output=True, timeout=10
            )
            if result.returncode != 0:
                reexec_with_better_python(test_import)
        except (OSError, subprocess.TimeoutExpired):
            reexec_with_better_python(test_import)


# ---------- 자동 설치 ----------
def auto_install(*packages):
    """미설치 패키지를 자동으로 pip install 시도.

    Returns:
        True if installation succeeded, False otherwise.
    """
    for attempt in range(2):
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', '--quiet']
            if attempt == 1:
                cmd.append('--break-system-packages')
            cmd.extend(packages)
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return False


# ---------- 한국어 폰트 탐색 ----------
_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_BUNDLED_FONT = os.path.join(_UTILS_DIR, '..', 'fonts', 'NanumGothic-Regular.ttf')

# 플랫폼별 폰트 검색 경로
# 1순위: 플러그인 번들 폰트 → 컨테이너 환경에서도 동작
# 2순위: macOS 시스템 폰트 (AppleGothic.ttf 우선, AppleSDGothicNeo.ttc는 CFF-in-TTC 문제)
# 3순위: Linux 시스템 폰트
FONT_SEARCH_PATHS = {
    'Darwin': [
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.otf',
        '/Library/Fonts/NanumGothic.ttf',
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
    ],
    'Linux': [
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/nanum/NanumGothic.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ],
}


def find_korean_font():
    """한국어 폰트 파일을 찾아 반환 (번들 폰트 → 시스템 폰트 → fc-list).

    Returns:
        폰트 파일 절대 경로 또는 None
    """
    # 1순위: 플러그인 번들 폰트
    bundled = os.path.abspath(_BUNDLED_FONT)
    if os.path.exists(bundled):
        return bundled

    # 2순위: 플랫폼별 시스템 폰트
    system = platform.system()
    for path in FONT_SEARCH_PATHS.get(system, []):
        if os.path.exists(path):
            return path

    # 3순위: fc-list fallback
    try:
        result = subprocess.run(
            ['fc-list', ':lang=ko', 'file'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                path = line.strip().rstrip(':').strip()
                if path and os.path.exists(path):
                    return path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def get_font_family_name(system=None):
    """CSS font-family 이름 (fallback용)."""
    system = system or platform.system()
    if system == 'Darwin':
        return "'Apple SD Gothic Neo', 'AppleGothic', sans-serif"
    elif system == 'Linux':
        return "'Noto Sans KR', 'NanumGothic', sans-serif"
    return "sans-serif"


def get_mono_family_name(system=None):
    """코드/Unicode 블록용 모노스페이스 font-family."""
    system = system or platform.system()
    if system == 'Darwin':
        return "'Menlo', 'Apple SD Gothic Neo', monospace"
    elif system == 'Linux':
        return "'D2Coding', 'Noto Sans Mono CJK KR', monospace"
    return "monospace"


# ---------- 안전한 파일 쓰기 ----------
def safe_write(path, data, encoding='utf-8'):
    """Atomic file write: 임시 파일에 쓴 후 os.replace()로 교체.

    Args:
        path: 대상 파일 경로
        data: 쓸 문자열 데이터
        encoding: 인코딩 (기본 utf-8)
    """
    abs_path = os.path.abspath(path)
    dir_path = os.path.dirname(abs_path)
    os.makedirs(dir_path, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(data)
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def safe_write_json(path, obj, indent=2, ensure_ascii=False):
    """JSON 데이터를 atomic write로 저장.

    Args:
        path: 대상 파일 경로
        obj: JSON으로 직렬화할 객체
        indent: 들여쓰기 (기본 2)
        ensure_ascii: ASCII 이스케이프 여부 (기본 False)
    """
    data = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii)
    safe_write(path, data + '\n')
