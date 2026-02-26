#!/usr/bin/env python3
"""
Smart Daily Briefing - Chart Generator

GA4 브리핑 데이터를 차트 이미지로 변환합니다.
- matplotlib 설치 시: PNG 차트 생성
- matplotlib 미설치 시: 순수 Python SVG 차트 생성

Usage:
    python3 scripts/generate-charts.py \
        --input briefings/charts/2026-02-11/data.json \
        --output-dir briefings/charts/2026-02-11/ \
        --format auto
"""

import argparse
import html
import json
import math
import os
import platform
import sys

# ---------- 공통 유틸리티 ----------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import ensure_best_python, auto_install, find_korean_font, safe_write, safe_write_json

# ---------- Python 자동 전환 (matplotlib 기준) ----------
ensure_best_python('import matplotlib')

# ---------- matplotlib 감지 & 자동 설치 ----------
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import matplotlib.ticker as ticker
    import matplotlib.text
    from matplotlib.patches import FancyBboxPatch
    HAS_MATPLOTLIB = True
except ImportError:
    print("matplotlib 미설치 → 자동 설치 시도...", file=sys.stderr)
    if auto_install('matplotlib'):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            import matplotlib.ticker as ticker
            import matplotlib.text
            from matplotlib.patches import FancyBboxPatch
            HAS_MATPLOTLIB = True
        except ImportError:
            HAS_MATPLOTLIB = False
    else:
        HAS_MATPLOTLIB = False

# ---------- 상수 ----------
COLORS = [
    '#3B82F6', '#6366F1', '#8B5CF6', '#0EA5E9', '#14B8A6',
    '#F59E0B', '#10B981', '#EF4444', '#EC4899', '#64748B',
]
BG_COLOR = '#FFFFFF'
TEXT_COLOR = '#1E293B'
GRID_COLOR = '#E2E8F0'
POSITIVE_COLOR = '#10B981'
NEGATIVE_COLOR = '#EF4444'

METRIC_LABELS = {
    'sessions': '세션',
    'totalUsers': '사용자',
    'newUsers': '신규 사용자',
    'bounceRate': '이탈률',
    'averageSessionDuration': '평균 세션 시간',
    'screenPageViews': '페이지뷰',
    'engagementRate': '참여율',
    'eventCount': '이벤트 수',
    'sessionsPerUser': '세션/사용자',
    'screenPageViewsPerSession': '페이지뷰/세션',
}


def format_number(value):
    """숫자를 가독성 좋게 포맷팅 (천 단위 콤마)."""
    if isinstance(value, str):
        try:
            value = float(value) if '.' in value else int(value)
        except ValueError:
            return value
    if isinstance(value, float):
        if value.is_integer():
            return f'{int(value):,}'
        return f'{value:,.1f}'
    return f'{value:,}'


def format_date(date_str):
    """YYYYMMDD -> MM/DD"""
    if not date_str:
        return '?'
    if len(date_str) == 8 and date_str.isdigit():
        return f'{date_str[4:6]}/{date_str[6:8]}'
    return date_str


# ============================================================
#  SVG Chart Generator (순수 Python, 의존성 없음)
# ============================================================
class SvgChartGenerator:

    def __init__(self, width=600, height=400):
        self.width = width
        self.height = height

    def _header(self, w=None, h=None):
        w = w or self.width
        h = h or self.height
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; '
            f'background: {BG_COLOR};">\n'
        )

    def _footer(self):
        return '</svg>\n'

    def _rect(self, x, y, w, h, fill, rx=0, opacity=1):
        return (
            f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}" rx="{rx}" opacity="{opacity}"/>\n'
        )

    def _text(self, x, y, text, size=12, fill=TEXT_COLOR, anchor='start', weight='normal'):
        escaped = html.escape(str(text))
        return (
            f'  <text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'dominant-baseline="middle">{escaped}</text>\n'
        )

    def _line(self, x1, y1, x2, y2, color=GRID_COLOR, width=1):
        return (
            f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}"/>\n'
        )

    def _arc_path(self, cx, cy, r, start_angle, end_angle):
        """SVG arc path 생성"""
        x1 = cx + r * math.cos(start_angle)
        y1 = cy + r * math.sin(start_angle)
        x2 = cx + r * math.cos(end_angle)
        y2 = cy + r * math.sin(end_angle)
        large_arc = 1 if (end_angle - start_angle) >= math.pi else 0
        return f'M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large_arc} 1 {x2} {y2} Z'

    # ----- 차트 유형별 생성 -----

    def generate_vertical_bar(self, title, labels, values, value_labels=None):
        """세로 막대 차트 (일별 트렌드용)"""
        n = len(labels)
        if n == 0:
            return self._empty_chart(title)

        margin = {'top': 50, 'right': 30, 'bottom': 50, 'left': 60}
        chart_w = self.width - margin['left'] - margin['right']
        chart_h = self.height - margin['top'] - margin['bottom']
        max_val = max(max(values), 1)
        bar_w = min(chart_w / n * 0.7, 40)
        gap = chart_w / n

        svg = self._header()
        svg += self._text(self.width / 2, 25, title, size=16, anchor='middle', weight='bold')

        # Y축 그리드
        for i in range(5):
            y = margin['top'] + chart_h * (1 - i / 4)
            val = max_val * i / 4
            svg += self._line(margin['left'], y, self.width - margin['right'], y)
            label_val = int(val) if val == int(val) else round(val, 1)
            svg += self._text(margin['left'] - 8, y, format_number(label_val), size=10, anchor='end')

        # 막대
        for i, (label, val) in enumerate(zip(labels, values)):
            x = margin['left'] + gap * i + (gap - bar_w) / 2
            bar_h = (val / max_val) * chart_h if max_val > 0 else 0
            y = margin['top'] + chart_h - bar_h
            svg += self._rect(x, y, bar_w, bar_h, COLORS[0], rx=2)
            svg += self._text(
                margin['left'] + gap * i + gap / 2,
                margin['top'] + chart_h + 20,
                label, size=10, anchor='middle',
            )
            if value_labels:
                svg += self._text(
                    x + bar_w / 2, y - 8,
                    value_labels[i], size=9, anchor='middle', fill='#5F6368',
                )

        svg += self._footer()
        return svg

    def generate_horizontal_bar(self, title, labels, values, show_percent=False):
        """가로 막대 차트 (트래픽 소스, 상위 페이지용)"""
        n = len(labels)
        if n == 0:
            return self._empty_chart(title)

        row_h = 32
        margin = {'top': 50, 'right': 100, 'bottom': 20, 'left': 160}
        h = margin['top'] + row_h * n + margin['bottom']
        chart_w = self.width - margin['left'] - margin['right']
        max_val = max(max(values), 1)
        total = sum(values) if show_percent else 0

        svg = self._header(self.width, h)
        svg += self._text(self.width / 2, 25, title, size=16, anchor='middle', weight='bold')

        for i, (label, val) in enumerate(zip(labels, values)):
            y = margin['top'] + row_h * i
            bar_w = (val / max_val) * chart_w if max_val > 0 else 0

            # 라벨 (길면 자름)
            display_label = label[:20] + '...' if len(label) > 20 else label
            svg += self._text(margin['left'] - 8, y + row_h / 2, display_label, size=11, anchor='end')

            # 배경 바
            svg += self._rect(margin['left'], y + 4, chart_w, row_h - 8, GRID_COLOR, rx=3)
            # 값 바
            svg += self._rect(margin['left'], y + 4, bar_w, row_h - 8, COLORS[i % len(COLORS)], rx=3)

            # 값 표시
            val_text = format_number(val)
            if show_percent and total > 0:
                val_text += f'  ({val / total:.1%})'
            svg += self._text(
                self.width - margin['right'] + 8, y + row_h / 2,
                val_text, size=11,
            )

        svg += self._footer()
        return svg

    def generate_pie(self, title, labels, values):
        """파이 차트 (디바이스 분포용)"""
        n = len(labels)
        if n == 0:
            return self._empty_chart(title)

        total = sum(values) if values else 1
        cx, cy, r = self.width / 2, self.height / 2 + 10, min(self.width, self.height) / 2 - 60

        svg = self._header()
        svg += self._text(self.width / 2, 25, title, size=16, anchor='middle', weight='bold')

        start = -math.pi / 2
        for i, (label, val) in enumerate(zip(labels, values)):
            angle = (val / total) * 2 * math.pi if total > 0 else 0

            # 100%에 가까운 단일 항목은 원으로 그림 (arc path 시작/끝 겹침 방지)
            if angle >= 2 * math.pi - 0.01:
                svg += f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{COLORS[i % len(COLORS)]}"/>\n'
                svg += self._text(cx, cy, f'{label} 100%', size=11, anchor='middle', fill='#FFFFFF', weight='bold')
                start = start + angle
                continue

            end = start + angle
            path = self._arc_path(cx, cy, r, start, end)
            svg += f'  <path d="{path}" fill="{COLORS[i % len(COLORS)]}"/>\n'

            # 라벨 위치 (파이 조각 중앙)
            mid = start + angle / 2
            lx = cx + (r * 0.65) * math.cos(mid)
            ly = cy + (r * 0.65) * math.sin(mid)
            pct = f'{val / total:.0%}' if total > 0 else '0%'
            if angle > 0.3:  # 너무 작은 조각은 라벨 생략
                svg += self._text(lx, ly, f'{label} {pct}', size=11, anchor='middle', fill='#FFFFFF', weight='bold')

            start = end

        # 범례 (3개씩 한 줄)
        cols = 3
        legend_x = 30
        col_w = (self.width - 2 * legend_x) / cols
        for i, (label, val) in enumerate(zip(labels, values)):
            row = i // cols
            col = i % cols
            x = legend_x + col * col_w
            legend_y = self.height - 25 - (((n - 1) // cols) - row) * 20
            svg += self._rect(x, legend_y - 6, 12, 12, COLORS[i % len(COLORS)], rx=2)
            pct = f'{val / total:.1%}' if total > 0 else '0%'
            svg += self._text(x + 18, legend_y, f'{label} ({format_number(val)}, {pct})', size=10)

        svg += self._footer()
        return svg

    def generate_change_bar(self, title, labels, changes, threshold=20):
        """양방향 가로 막대 (변화율 표시)"""
        n = len(labels)
        if n == 0:
            return self._empty_chart(title)

        row_h = 36
        margin = {'top': 50, 'right': 80, 'bottom': 20, 'left': 120}
        h = margin['top'] + row_h * n + margin['bottom']
        half_w = (self.width - margin['left'] - margin['right']) / 2
        center_x = margin['left'] + half_w
        max_abs = max(abs(c) for c in changes) if changes else 1

        svg = self._header(self.width, h)
        svg += self._text(self.width / 2, 25, title, size=16, anchor='middle', weight='bold')

        # 중앙선
        svg += self._line(center_x, margin['top'] - 5, center_x, margin['top'] + row_h * n + 5, '#9AA0A6', 2)

        for i, (label, change) in enumerate(zip(labels, changes)):
            y = margin['top'] + row_h * i
            bar_w = (abs(change) / max_abs) * half_w if max_abs > 0 else 0
            color = POSITIVE_COLOR if change >= 0 else NEGATIVE_COLOR
            is_anomaly = abs(change) >= threshold

            if change >= 0:
                svg += self._rect(center_x, y + 6, bar_w, row_h - 12, color, rx=3)
            else:
                svg += self._rect(center_x - bar_w, y + 6, bar_w, row_h - 12, color, rx=3)

            svg += self._text(margin['left'] - 8, y + row_h / 2, label, size=11, anchor='end')

            sign = '+' if change >= 0 else ''
            val_text = f'{sign}{change:.1f}%'
            if is_anomaly:
                val_text += ' [!]'
            val_x = self.width - margin['right'] + 8
            svg += self._text(val_x, y + row_h / 2, val_text, size=11, fill=color, weight='bold')

        svg += self._footer()
        return svg

    def _empty_chart(self, title):
        svg = self._header()
        svg += self._text(self.width / 2, self.height / 2, f'{title}: 데이터 없음', size=14, anchor='middle')
        svg += self._footer()
        return svg



# ============================================================
#  Matplotlib Chart Generator (프로페셔널 대시보드 스타일)
# ============================================================
class MatplotlibChartGenerator:

    # Slate Blue 팔레트 (차분한 블루-그레이 계열)
    PALETTE = ['#3B82F6', '#6366F1', '#8B5CF6', '#0EA5E9', '#14B8A6',
               '#F59E0B', '#10B981', '#EF4444', '#EC4899', '#64748B']
    ACCENT = '#3B82F6'
    SUBTLE_TEXT = '#64748B'
    AXIS_COLOR = '#E2E8F0'
    GRID_ALPHA = 0.25

    def __init__(self):
        self._setup_font()
        self._apply_global_style()

    def _setup_font(self):
        """폰트 파일을 직접 등록하여 환경에 무관하게 한국어 렌더링"""
        self._font_prop = None

        font_path = find_korean_font()
        if font_path:
            try:
                fm.fontManager.addfont(font_path)
            except Exception:
                pass
            self._font_prop = fm.FontProperties(fname=font_path)
            font_name = self._font_prop.get_name()
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams.get('font.sans-serif', [])
            print(f"  Font: {font_name} ({font_path})", file=sys.stderr)
        else:
            system = platform.system()
            if system == 'Darwin':
                plt.rcParams['font.family'] = 'AppleGothic'
            elif system == 'Linux':
                plt.rcParams['font.family'] = 'NanumGothic'
            print(f"  Font: fallback ({plt.rcParams['font.family']})", file=sys.stderr)
        plt.rcParams['axes.unicode_minus'] = False

    def _apply_global_style(self):
        """전역 스타일: 깔끔한 대시보드 룩"""
        plt.rcParams.update({
            'axes.unicode_minus': False,
            'figure.facecolor': '#FFFFFF',
            'axes.facecolor': '#FFFFFF',
            'axes.edgecolor': self.AXIS_COLOR,
            'axes.linewidth': 0.8,
            'axes.grid': False,
            'xtick.color': self.SUBTLE_TEXT,
            'ytick.color': self.SUBTLE_TEXT,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'text.color': TEXT_COLOR,
            'figure.dpi': 150,
            'savefig.dpi': 150,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.3,
        })

    def _fp(self, **kwargs):
        """fontproperties가 있으면 kwargs에 추가하는 헬퍼"""
        if self._font_prop:
            kwargs['fontproperties'] = self._font_prop
        return kwargs

    def _clean_axes(self, ax, grid_axis='y'):
        """공통: 상단/우측 spine 제거, 미니멀 그리드"""
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(self.AXIS_COLOR)
        ax.spines['bottom'].set_color(self.AXIS_COLOR)
        ax.tick_params(axis='both', which='both', length=0, pad=6)
        if grid_axis:
            ax.grid(axis=grid_axis, alpha=self.GRID_ALPHA, linestyle='--',
                    color=self.AXIS_COLOR, linewidth=0.6)

    def _set_title(self, ax, title):
        """좌측 정렬 + 하단 액센트 라인 타이틀"""
        kwargs = dict(fontsize=13, fontweight='bold', color=TEXT_COLOR,
                      loc='left', pad=16)
        if self._font_prop:
            kwargs['fontproperties'] = self._font_prop
        ax.set_title(title, **kwargs)
        # 타이틀 아래 얇은 액센트 라인
        ax.annotate('', xy=(0, 1.02), xycoords='axes fraction',
                    xytext=(0.15, 1.02), textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='-', color=self.ACCENT, lw=2.5))

    def _apply_font_to_all(self, fig):
        """figure 내 모든 Text 객체에 fontproperties를 강제 적용 (rcParams 불안정 대응)"""
        if not self._font_prop:
            return
        for text_obj in fig.findobj(matplotlib.text.Text):
            text_obj.set_fontproperties(self._font_prop)

    def generate_daily_trend(self, title, labels, sessions, users=None, *, output_path):
        """일별 트렌드: 바 + 라인 복합 차트"""
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        self._clean_axes(ax1)

        x = range(len(labels))
        bar_width = 0.55

        # 막대 차트
        ax1.bar(x, sessions, color=self.PALETTE[0], alpha=0.85,
                width=bar_width, edgecolor='white', linewidth=0.5,
                label='세션', zorder=3)

        ax1.set_ylabel('세션', **self._fp(fontsize=10, color=self.PALETTE[0], fontweight='600'))
        ax1.tick_params(axis='y', labelcolor=self.PALETTE[0])
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, **self._fp(rotation=0, ha='center', fontsize=9))
        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: format_number(int(v))))

        if users:
            ax2 = ax1.twinx()
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_color(self.AXIS_COLOR)
            ax2.tick_params(axis='both', which='both', length=0, pad=6)
            ax2.plot(x, users, color=self.PALETTE[1], marker='o', markersize=6,
                     linewidth=2.5, label='사용자', zorder=4,
                     markerfacecolor='white', markeredgewidth=2,
                     markeredgecolor=self.PALETTE[1])
            ax2.set_ylabel('사용자', **self._fp(fontsize=10, color=self.PALETTE[1], fontweight='600'))
            ax2.tick_params(axis='y', labelcolor=self.PALETTE[1])
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: format_number(int(v))))

            # 통합 범례
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            legend = ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                       frameon=True, framealpha=0.9, edgecolor=self.AXIS_COLOR,
                       fontsize=9, borderpad=0.8)
            if self._font_prop:
                for text in legend.get_texts():
                    text.set_fontproperties(self._font_prop)

        self._set_title(ax1, title)
        self._apply_font_to_all(fig)
        fig.tight_layout()
        fig.savefig(output_path, facecolor='white')
        plt.close(fig)

    def generate_horizontal_bar(self, title, labels, values, show_percent=False, *, output_path):
        """가로 막대 차트"""
        n = len(labels)
        fig_height = max(3.5, n * 0.65 + 1.5)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        self._clean_axes(ax, grid_axis='x')
        ax.spines['left'].set_visible(False)

        display_labels = [l[:28] + '...' if len(l) > 28 else l for l in labels]
        colors = [self.PALETTE[i % len(self.PALETTE)] for i in range(n)]
        max_val = max(values) if values else 1
        total = sum(values) if show_percent else 0

        # 배경 바 (프로그레스 바 스타일)
        for i in range(n):
            ax.barh(i, max_val * 1.02, height=0.55, color='#F1F3F4',
                    edgecolor='none', zorder=1)

        # 값 바
        bars = ax.barh(range(n), values, height=0.55, color=colors,
                       edgecolor='white', linewidth=0.3, zorder=2)

        ax.set_yticks(range(n))
        if self._font_prop:
            ax.set_yticklabels(display_labels, fontsize=10, fontproperties=self._font_prop)
        else:
            ax.set_yticklabels(display_labels, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlim(0, max_val * 1.25)
        ax.xaxis.set_visible(False)

        # 값 라벨
        for i, (bar, val) in enumerate(zip(bars, values)):
            text = format_number(val)
            if show_percent and total > 0:
                text += f'  ({val / total:.1%})'
            ax.text(bar.get_width() + max_val * 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    text, va='center', fontsize=9.5, color=self.SUBTLE_TEXT,
                    fontweight='500')

        self._set_title(ax, title)
        self._apply_font_to_all(fig)
        fig.tight_layout()
        fig.savefig(output_path, facecolor='white')
        plt.close(fig)

    def generate_pie(self, title, labels, values, *, output_path):
        """도넛 차트 (중앙에 총합 표시)"""
        fig, ax = plt.subplots(figsize=(7, 5.5))
        colors = [self.PALETTE[i % len(self.PALETTE)] for i in range(len(labels))]
        total = sum(values) if values else 1

        wedges, texts, autotexts = ax.pie(
            values, labels=None, colors=colors,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
            startangle=90, pctdistance=0.78,
            wedgeprops={'width': 0.38, 'edgecolor': 'white', 'linewidth': 2.5},
        )
        for t in autotexts:
            t.set_fontsize(9.5)
            t.set_fontweight('bold')
            t.set_color('#444444')

        # 중앙 총합 표시
        ax.text(0, 0.06, format_number(total), ha='center', va='center',
                **self._fp(fontsize=20, fontweight='bold', color=TEXT_COLOR))
        ax.text(0, -0.12, '총합', ha='center', va='center',
                **self._fp(fontsize=9, color=self.SUBTLE_TEXT))

        # 깔끔한 범례 (박스 스타일)
        legend = ax.legend(
            [f'{l}  {format_number(v)}' for l, v in zip(labels, values)],
            loc='lower center', bbox_to_anchor=(0.5, -0.08),
            ncol=min(len(labels), 3), fontsize=9,
            frameon=True, framealpha=0.9, edgecolor=self.AXIS_COLOR,
            borderpad=0.8, columnspacing=2,
            handlelength=1.2, handleheight=0.8,
        )
        legend.get_frame().set_linewidth(0.6)
        if self._font_prop:
            for text in legend.get_texts():
                text.set_fontproperties(self._font_prop)

        self._set_title(ax, title)
        self._apply_font_to_all(fig)
        fig.tight_layout()
        fig.savefig(output_path, facecolor='white')
        plt.close(fig)

    def generate_change_bar(self, title, labels, changes, threshold=20, *, output_path):
        """양방향 가로 막대 (변화율) - 이상치 하이라이트"""
        n = len(labels)
        fig_height = max(3.5, n * 0.7 + 1.5)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        self._clean_axes(ax, grid_axis=None)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        max_abs = max(abs(c) for c in changes) if changes else 1

        for i, (label, change) in enumerate(zip(labels, changes)):
            is_anomaly = abs(change) >= threshold
            color = POSITIVE_COLOR if change >= 0 else NEGATIVE_COLOR
            alpha = 0.9 if is_anomaly else 0.7

            # 막대
            bar = ax.barh(i, change, height=0.55, color=color, alpha=alpha,
                          edgecolor='white', linewidth=0.3, zorder=2)

            # 이상치 마커
            if is_anomaly:
                ax.barh(i, change, height=0.55, color=color, alpha=0.15,
                        edgecolor=color, linewidth=1.5, linestyle='--', zorder=1)

            # 값 라벨
            sign = '+' if change >= 0 else ''
            text = f'{sign}{change:.1f}%'
            if is_anomaly:
                text += '  [!]'
            offset = max_abs * 0.06 * (1 if change >= 0 else -1)
            ax.text(change + offset, i,
                    text, va='center', fontsize=10, fontweight='bold',
                    color=color,
                    ha='left' if change >= 0 else 'right')

        # 중앙선
        ax.axvline(x=0, color='#9AA0A6', linewidth=1.2, zorder=3)

        ax.set_yticks(range(n))
        if self._font_prop:
            ax.set_yticklabels(labels, fontsize=10, fontproperties=self._font_prop)
        else:
            ax.set_yticklabels(labels, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlim(-max_abs * 1.5, max_abs * 1.5)
        ax.xaxis.set_visible(False)

        self._set_title(ax, title)
        self._apply_font_to_all(fig)
        fig.tight_layout()
        fig.savefig(output_path, facecolor='white')
        plt.close(fig)


# ============================================================
#  Chart Dispatcher
# ============================================================
class ChartDispatcher:

    def __init__(self, output_dir, fmt='auto'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        if fmt == 'auto':
            self.use_matplotlib = HAS_MATPLOTLIB
        elif fmt == 'png':
            if not HAS_MATPLOTLIB:
                print('ERROR: --format png requires matplotlib. Install: pip install matplotlib', file=sys.stderr)
                sys.exit(1)
            self.use_matplotlib = True
        else:
            self.use_matplotlib = False

        self.ext = 'png' if self.use_matplotlib else 'svg'
        self.svg_gen = None if self.use_matplotlib else SvgChartGenerator()
        self.mpl_gen = MatplotlibChartGenerator() if self.use_matplotlib else None
        self.manifest = {'format': self.ext, 'charts': {}}

    def _output_path(self, name):
        return os.path.join(self.output_dir, f'{name}.{self.ext}')

    def generate_daily_trend(self, section_data):
        rows = section_data.get('data', [])
        if not rows:
            return

        labels = [format_date(r.get('date', '')) for r in rows]
        sessions = [r.get('sessions', 0) for r in rows]
        users = [r.get('totalUsers', 0) for r in rows]
        title = section_data.get('name', '일별 트렌드')
        path = self._output_path('daily_trend')

        if self.use_matplotlib:
            self.mpl_gen.generate_daily_trend(title, labels, sessions, users, output_path=path)
        else:
            svg = self.svg_gen.generate_vertical_bar(
                title, labels, sessions,
                value_labels=[format_number(v) for v in sessions],
            )
            safe_write(path, svg)

        self.manifest['charts']['daily_trend'] = f'daily_trend.{self.ext}'

    def generate_traffic_sources(self, section_data):
        self.generate_horizontal_bar_generic(
            'traffic_sources', section_data,
            label_keys=['sessionSource', 'sessionMedium'],
            value_key='sessions', show_percent=True,
        )

    def generate_device(self, section_data):
        rows = section_data.get('data', [])
        if not rows:
            return

        labels = [r.get('deviceCategory', '?') for r in rows]
        values = [r.get('sessions', 0) for r in rows]
        title = section_data.get('name', '디바이스별 분석')
        path = self._output_path('device')

        if self.use_matplotlib:
            self.mpl_gen.generate_pie(title, labels, values, output_path=path)
        else:
            svg = self.svg_gen.generate_pie(title, labels, values)
            safe_write(path, svg)

        self.manifest['charts']['device'] = f'device.{self.ext}'

    def generate_horizontal_bar_generic(self, section_id, section_data, label_keys, value_key, show_percent=False):
        """범용 가로 막대 차트 생성"""
        rows = section_data.get('data', [])
        if not rows:
            return

        labels = []
        for r in rows:
            parts = [str(r.get(k, '?')) for k in label_keys]
            labels.append('/'.join(parts) if len(parts) > 1 else parts[0])
        values = [r.get(value_key, 0) for r in rows]
        title = section_data.get('name', section_id)
        path = self._output_path(section_id)

        if self.use_matplotlib:
            self.mpl_gen.generate_horizontal_bar(title, labels, values, show_percent=show_percent, output_path=path)
        else:
            svg = self.svg_gen.generate_horizontal_bar(title, labels, values, show_percent=show_percent)
            safe_write(path, svg)

        self.manifest['charts'][section_id] = f'{section_id}.{self.ext}'

    def generate_top_pages(self, section_data):
        self.generate_horizontal_bar_generic(
            'top_pages', section_data,
            label_keys=['pagePath'], value_key='screenPageViews',
        )

    def generate_landing_pages(self, section_data):
        self.generate_horizontal_bar_generic(
            'landing_pages', section_data,
            label_keys=['landingPage'], value_key='sessions',
        )

    def generate_campaigns(self, section_data):
        self.generate_horizontal_bar_generic(
            'campaigns', section_data,
            label_keys=['sessionCampaignName', 'sessionSource'],
            value_key='sessions', show_percent=True,
        )

    def generate_events(self, section_data):
        self.generate_horizontal_bar_generic(
            'events', section_data,
            label_keys=['eventName'], value_key='eventCount',
        )

    def _build_change_data(self, section_data):
        """compare_previous 섹션에서 변화율 데이터를 추출"""
        data = section_data.get('data', {})
        if isinstance(data, list):
            return [], []  # 배열 형태의 데이터는 변화율 차트 대상이 아님
        current = data.get('current', {})
        previous = data.get('previous', {})
        if not current or not previous:
            return [], []

        labels = []
        changes = []
        for key in current:
            if key not in previous:
                continue
            try:
                cur = float(current[key])
                prev = float(previous[key])
            except (ValueError, TypeError):
                continue
            if prev == 0:
                if cur != 0:
                    label = METRIC_LABELS.get(key, key)
                    labels.append(label)
                    changes.append(100.0)  # 0→N을 +100%로 표시
                continue
            change = ((cur - prev) / abs(prev)) * 100
            label = METRIC_LABELS.get(key, key)
            labels.append(label)
            changes.append(change)

        return labels, changes

    def _generate_change_chart(self, chart_id, section_data, threshold=20):
        """변화율 차트 생성 공통 로직"""
        labels, changes = self._build_change_data(section_data)
        if not labels:
            return

        title = section_data.get('name', '변화율')
        path = self._output_path(chart_id)

        if self.use_matplotlib:
            self.mpl_gen.generate_change_bar(title, labels, changes, threshold, output_path=path)
        else:
            svg = self.svg_gen.generate_change_bar(title, labels, changes, threshold)
            safe_write(path, svg)

        self.manifest['charts'][chart_id] = f'{chart_id}.{self.ext}'

    def generate_overview_change(self, section_data, threshold=20):
        self._generate_change_chart('overview_change', section_data, threshold)

    def generate_user_behavior(self, section_data, threshold=20):
        self._generate_change_chart('user_behavior', section_data, threshold)

    def save_manifest(self):
        path = os.path.join(self.output_dir, 'manifest.json')
        safe_write_json(path, self.manifest)


# ============================================================
#  섹션 ID → 생성 함수 매핑
# ============================================================
SECTION_HANDLERS = {
    'daily_trend': 'generate_daily_trend',
    'traffic_sources': 'generate_traffic_sources',
    'campaigns': 'generate_campaigns',
    'device': 'generate_device',
    'top_pages': 'generate_top_pages',
    'landing_pages': 'generate_landing_pages',
    'events': 'generate_events',
    'overview': 'generate_overview_change',
    'user_behavior': 'generate_user_behavior',
    # 주간 차트 (v1.11.0): 기존 핸들러 재사용
    'weekly_trend': 'generate_daily_trend',
    'weekly_comparison': 'generate_overview_change',
}


# ============================================================
#  Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Smart Daily Briefing - Chart Generator')
    parser.add_argument('--input', required=True, help='입력 JSON 파일 경로')
    parser.add_argument('--output-dir', required=True, help='차트 이미지 출력 디렉토리')
    parser.add_argument('--format', choices=['auto', 'png', 'svg'], default='auto', help='출력 형식')
    args = parser.parse_args()

    if sys.version_info < (3, 9):
        print('ERROR: Python 3.9 이상이 필요합니다.', file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f'ERROR: 입력 파일을 읽을 수 없습니다: {e}', file=sys.stderr)
        sys.exit(1)

    threshold = data.get('anomaly_threshold', 20)
    sections = data.get('sections', {})

    dispatcher = ChartDispatcher(args.output_dir, args.format)
    backend = 'matplotlib (PNG)' if dispatcher.use_matplotlib else 'SVG (pure Python)'
    print(f'Chart backend: {backend}')

    for section_id, section_data in sections.items():
        handler_name = SECTION_HANDLERS.get(section_id)
        if not handler_name:
            continue

        prev_count = len(dispatcher.manifest['charts'])
        handler = getattr(dispatcher, handler_name)
        if handler_name in ('generate_overview_change', 'generate_user_behavior'):
            handler(section_data, threshold)
        else:
            handler(section_data)

        if len(dispatcher.manifest['charts']) > prev_count:
            print(f'  Generated: {section_id}.{dispatcher.ext}')
        else:
            print(f'  Skipped: {section_id} (no data)')

    dispatcher.save_manifest()
    print(f'Manifest saved: {os.path.join(args.output_dir, "manifest.json")}')
    print(f'Total charts: {len(dispatcher.manifest["charts"])}')


if __name__ == '__main__':
    main()
