#!/usr/bin/env python3
"""
Smart Daily Briefing - PDF Generator

마크다운 브리핑을 PDF로 변환합니다.
- weasyprint + markdown 설치 시: 마크다운 → HTML → PDF
- 미설치 시: 설치 안내 메시지 출력

Usage:
    python3 scripts/generate-pdf.py \
        --input briefings/2026-02-15.md \
        --output briefings/2026-02-15.pdf \
        --charts-dir briefings/charts/2026-02-15/
"""

import argparse
import glob
import os
import platform
import re
import subprocess
import sys

# ---------- Python 자동 전환 ----------
# weasyprint가 없는 Python으로 실행된 경우, weasyprint가 있는 Python을 찾아 재실행
def _reexec_with_weasyprint():
    """weasyprint가 있는 Python을 찾아 현재 스크립트를 다시 실행"""
    candidates = [
        '/opt/homebrew/bin/python3.13',
        '/opt/homebrew/bin/python3.12',
        '/opt/homebrew/bin/python3.11',
        '/usr/local/bin/python3',
        '/usr/bin/python3',
    ]
    for py in candidates:
        if py == sys.executable or not os.path.exists(py):
            continue
        try:
            result = subprocess.run(
                [py, '-c', 'from weasyprint import HTML'],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                print(f"  Re-exec with: {py}", file=sys.stderr)
                os.execv(py, [py] + sys.argv)
        except (OSError, subprocess.TimeoutExpired):
            continue

try:
    from weasyprint import HTML as _wp_test
    del _wp_test
except ImportError:
    _reexec_with_weasyprint()

# ---------- 의존성 감지 & 자동 설치 ----------
def _auto_install(*packages):
    """미설치 패키지를 자동으로 pip install 시도"""
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

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    print("weasyprint 미설치 → 자동 설치 시도...", file=sys.stderr)
    if _auto_install('weasyprint'):
        try:
            from weasyprint import HTML
            HAS_WEASYPRINT = True
        except ImportError:
            HAS_WEASYPRINT = False
    else:
        HAS_WEASYPRINT = False

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    print("markdown 미설치 → 자동 설치 시도...", file=sys.stderr)
    if _auto_install('markdown'):
        try:
            import markdown
            HAS_MARKDOWN = True
        except ImportError:
            HAS_MARKDOWN = False
    else:
        HAS_MARKDOWN = False

# ---------- PDF 스타일 상수 (generate-charts.py Slate Blue 팔레트 기반) ----------
PRIMARY_COLOR = '#3B82F6'
TEXT_COLOR = '#1E293B'
SECONDARY_TEXT = '#64748B'
BORDER_COLOR = '#E2E8F0'
BG_LIGHT = '#F8FAFC'
POSITIVE_COLOR = '#10B981'
NEGATIVE_COLOR = '#EF4444'


# ---------- 한국어 폰트 ----------

# 플랫폼별 한국어 폰트 검색 경로 (우선순위 순)
FONT_SEARCH = {
    'Darwin': [
        # macOS 시스템 폰트
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.otf',
        '/Library/Fonts/NanumGothic.ttf',
    ],
    'Linux': [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/nanum/NanumGothic.ttf',
    ],
}


def _find_font_file(candidates):
    """후보 경로 목록에서 존재하는 첫 번째 폰트 파일 반환"""
    for path in candidates:
        # glob 패턴 지원 (예: /usr/share/fonts/**/NanumGothic.ttf)
        matches = glob.glob(path)
        if matches:
            return matches[0]
        if os.path.exists(path):
            return path

    # fc-list fallback: fontconfig로 한국어 폰트 검색
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


def get_font_face_css():
    """@font-face CSS를 생성하여 weasyprint가 한국어 폰트를 확실히 찾도록 함"""
    system = platform.system()
    candidates = FONT_SEARCH.get(system, [])
    font_path = _find_font_file(candidates)

    if not font_path:
        # 폰트 파일을 찾지 못하면 font-family 이름만 사용 (fallback)
        return '', _get_font_family_name(system), _get_mono_family_name(system)

    font_uri = f'file://{os.path.abspath(font_path)}'

    font_face_css = f"""
  @font-face {{
    font-family: 'BriefingFont';
    src: url('{font_uri}');
    font-weight: normal;
    font-style: normal;
  }}
  @font-face {{
    font-family: 'BriefingFont';
    src: url('{font_uri}');
    font-weight: bold;
    font-style: normal;
  }}"""

    font_family = f"'BriefingFont', {_get_font_family_name(system)}"
    mono_family = f"{_get_mono_family_name(system)}"

    return font_face_css, font_family, mono_family


def _get_font_family_name(system):
    """CSS font-family 이름 (fallback용)"""
    if system == 'Darwin':
        return "'Apple SD Gothic Neo', 'AppleGothic', sans-serif"
    elif system == 'Linux':
        return "'Noto Sans KR', 'NanumGothic', sans-serif"
    return "sans-serif"


def _get_mono_family_name(system):
    """코드/Unicode 블록용 모노스페이스 font-family"""
    if system == 'Darwin':
        return "'Menlo', 'Apple SD Gothic Neo', monospace"
    elif system == 'Linux':
        return "'D2Coding', 'Noto Sans Mono CJK KR', monospace"
    return "monospace"


# ---------- HTML 템플릿 ----------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  {font_face}
  @page {{
    size: A4;
    margin: 2cm 2cm 2.5cm 2cm;
    @top-center {{
      content: "Smart Daily Briefing";
      font-size: 8pt;
      color: {secondary_text};
    }}
    @bottom-center {{
      content: "Page " counter(page) " / " counter(pages);
      font-size: 8pt;
      color: {secondary_text};
    }}
  }}
  body {{
    font-family: {font};
    font-size: 10.5pt;
    line-height: 1.7;
    color: {text_color};
  }}
  h1 {{
    font-size: 18pt;
    border-bottom: 2px solid {primary};
    padding-bottom: 6pt;
    margin-top: 0;
  }}
  h2 {{
    font-size: 14pt;
    color: {primary};
    margin-top: 20pt;
    border-bottom: 1px solid {border};
    padding-bottom: 4pt;
  }}
  h3 {{
    font-size: 12pt;
    color: {text_color};
    margin-top: 14pt;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
    font-size: 9.5pt;
  }}
  th, td {{
    border: 1px solid {border};
    padding: 6pt 10pt;
    text-align: left;
  }}
  th {{
    background-color: {bg_light};
    font-weight: bold;
  }}
  tr:nth-child(even) {{
    background-color: #FAFAFA;
  }}
  img {{
    max-width: 100%;
    height: auto;
    margin: 10pt 0;
    display: block;
  }}
  blockquote {{
    border-left: 3px solid {primary};
    padding-left: 12pt;
    color: {secondary_text};
    margin: 10pt 0;
    font-size: 10pt;
  }}
  code {{
    background: {bg_light};
    padding: 1pt 4pt;
    border-radius: 3pt;
    font-family: {mono_font};
    font-size: 9pt;
  }}
  pre {{
    background: {bg_light};
    padding: 10pt;
    border-radius: 4pt;
    overflow-x: auto;
    white-space: pre-wrap;
    font-family: {mono_font};
    font-size: 8.5pt;
    line-height: 1.4;
  }}
  ul, ol {{
    padding-left: 20pt;
  }}
  li {{
    margin-bottom: 4pt;
  }}
  hr {{
    border: none;
    border-top: 1px solid {border};
    margin: 16pt 0;
  }}
  strong {{
    color: {text_color};
  }}
</style>
</head>
<body>
{content}
</body>
</html>"""


def resolve_image_paths(html_content, base_dir, charts_dir=None):
    """HTML 내 상대 경로 이미지를 file:// 절대 경로로 변환"""
    search_dirs = [base_dir]
    if charts_dir and os.path.isdir(charts_dir):
        search_dirs.append(os.path.abspath(charts_dir))

    def replace_src(match):
        src = match.group(1)
        if src.startswith(('http://', 'https://', 'file://', 'data:')):
            return match.group(0)
        for d in search_dirs:
            abs_path = os.path.abspath(os.path.join(d, src))
            if os.path.exists(abs_path):
                return f'src="file://{abs_path}"'
        return match.group(0)

    return re.sub(r'src="([^"]+)"', replace_src, html_content)


def md_to_html(md_content):
    """마크다운을 HTML로 변환"""
    return markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'nl2br'],
        output_format='html5'
    )


def generate_pdf(input_path, output_path, charts_dir=None):
    """마크다운 파일을 PDF로 변환"""
    # 마크다운 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 마크다운 → HTML 변환
    html_body = md_to_html(md_content)

    # 이미지 경로를 절대경로로 변환
    base_dir = os.path.dirname(os.path.abspath(input_path))
    html_body = resolve_image_paths(html_body, base_dir, charts_dir)

    # 한국어 폰트 @font-face 생성
    font_face_css, font_family, mono_family = get_font_face_css()

    # HTML 템플릿에 래핑
    full_html = HTML_TEMPLATE.format(
        content=html_body,
        font_face=font_face_css,
        font=font_family,
        mono_font=mono_family,
        primary=PRIMARY_COLOR,
        text_color=TEXT_COLOR,
        secondary_text=SECONDARY_TEXT,
        border=BORDER_COLOR,
        bg_light=BG_LIGHT,
    )

    # 출력 디렉토리 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # PDF 생성
    HTML(string=full_html, base_url=base_dir).write_pdf(output_path)

    file_size = os.path.getsize(output_path)
    size_str = f"{file_size / 1024:.0f}KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f}MB"
    print(f"OK: {output_path} ({size_str})")
    return True


def main():
    parser = argparse.ArgumentParser(description='Smart Daily Briefing - PDF Generator')
    parser.add_argument('--input', required=True, help='입력 마크다운 파일 경로')
    parser.add_argument('--output', required=True, help='출력 PDF 파일 경로')
    parser.add_argument('--charts-dir', default=None, help='차트 이미지 디렉토리 (선택)')
    args = parser.parse_args()

    # 의존성 확인
    if not HAS_WEASYPRINT:
        print("ERROR: weasyprint가 설치되지 않았습니다.", file=sys.stderr)
        print("설치: pip install weasyprint", file=sys.stderr)
        sys.exit(1)

    if not HAS_MARKDOWN:
        print("ERROR: markdown 라이브러리가 설치되지 않았습니다.", file=sys.stderr)
        print("설치: pip install markdown", file=sys.stderr)
        sys.exit(1)

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(f"ERROR: 입력 파일을 찾을 수 없습니다: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        generate_pdf(args.input, args.output, args.charts_dir)
    except Exception as e:
        print(f"ERROR: PDF 생성 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
