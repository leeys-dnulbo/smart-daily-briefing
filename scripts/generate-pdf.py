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
import os
import platform
import re
import sys

# ---------- 공통 유틸리티 ----------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import ensure_best_python, auto_install, find_korean_font, get_font_family_name, get_mono_family_name

# ---------- Python 자동 전환 (weasyprint 기준) ----------
ensure_best_python('from weasyprint import HTML')

# ---------- 의존성 감지 & 자동 설치 ----------
try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    print("weasyprint 미설치 → 자동 설치 시도...", file=sys.stderr)
    if auto_install('weasyprint'):
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
    if auto_install('markdown'):
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


# ---------- 한국어 폰트 (utils.py 활용) ----------

def get_font_face_css():
    """@font-face CSS를 생성하여 weasyprint가 한국어 폰트를 확실히 찾도록 함"""
    system = platform.system()
    font_path = find_korean_font()

    if not font_path:
        return '', get_font_family_name(system), get_mono_family_name(system)

    abs_font_path = os.path.abspath(font_path)
    # URI 특수문자 이스케이프 (CSS injection 방지)
    from urllib.parse import quote
    font_uri = 'file://' + quote(abs_font_path, safe='/:@')

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

    font_family = f"'BriefingFont', {get_font_family_name(system)}"
    mono_family = f"{get_mono_family_name(system)}"

    return font_face_css, font_family, mono_family


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
    search_dirs = [os.path.abspath(base_dir)]
    if charts_dir and os.path.isdir(charts_dir):
        search_dirs.append(os.path.abspath(charts_dir))

    def replace_src(match):
        src = match.group(1)
        if src.startswith(('http://', 'https://', 'file://', 'data:')):
            return match.group(0)
        for d in search_dirs:
            abs_path = os.path.abspath(os.path.join(d, src))
            # Path Traversal 방어: 해석된 경로가 허용된 디렉토리 하위인지 확인
            if not abs_path.startswith(d + os.sep) and abs_path != d:
                continue
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
    # html_body 내 중괄호({})가 str.format과 충돌하지 않도록 이스케이프
    safe_body = html_body.replace('{', '&#123;').replace('}', '&#125;')
    full_html = HTML_TEMPLATE.format(
        content=safe_body,
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
