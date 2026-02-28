"""tests/test_generate_charts.py — 커스텀 섹션 차트 생성 테스트

generate-charts.py는 모듈 로딩 시 ensure_best_python()으로 Python을 재실행하므로
직접 import 하면 테스트가 무한루프에 빠질 수 있습니다.
따라서 모듈의 부작용(re-exec, matplotlib 설치)을 우회하여 로드합니다.
"""

import importlib
import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


def _load_generate_charts():
    """generate-charts.py를 부작용 없이 로드."""
    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    )
    # utils 모듈을 먼저 로드 (ensure_best_python 등 포함)
    utils_path = os.path.join(scripts_dir, "utils.py")
    utils_spec = importlib.util.spec_from_file_location("utils", utils_path)
    utils_mod = importlib.util.module_from_spec(utils_spec)
    # ensure_best_python을 no-op으로 대체
    sys.modules["utils"] = utils_mod
    utils_spec.loader.exec_module(utils_mod)
    utils_mod.ensure_best_python = lambda test_import: None
    utils_mod.auto_install = lambda *pkgs: False

    # generate-charts.py 로드
    chart_path = os.path.join(scripts_dir, "generate-charts.py")
    spec = importlib.util.spec_from_file_location("generate_charts", chart_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_charts"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_generate_charts()
infer_chart_type = _mod.infer_chart_type
ChartDispatcher = _mod.ChartDispatcher
SECTION_HANDLERS = _mod.SECTION_HANDLERS
HAS_MATPLOTLIB = _mod.HAS_MATPLOTLIB


# ========== infer_chart_type 테스트 ==========


class TestChartTypeInference:
    """infer_chart_type() 자동 추론 규칙 테스트."""

    def test_date_dimension_returns_line(self):
        """dimensions에 date 포함 → line."""
        section = {"dimensions": ["date"], "metrics": ["sessions"]}
        assert infer_chart_type(section) == "line"

    def test_date_with_other_dims_returns_line(self):
        """dimensions에 date 포함 (다른 차원과 함께) → line."""
        section = {"dimensions": ["date", "deviceCategory"], "metrics": ["sessions"]}
        assert infer_chart_type(section) == "line"

    def test_dimensions_with_limit_returns_horizontal_bar(self):
        """dimensions + limit > 0 → horizontal_bar."""
        section = {"dimensions": ["pagePath"], "metrics": ["screenPageViews"], "limit": 10}
        assert infer_chart_type(section) == "horizontal_bar"

    def test_no_dimensions_compare_previous_returns_change_bar(self):
        """빈 dimensions + compare_previous → change_bar."""
        section = {"dimensions": [], "metrics": ["sessions"], "compare_previous": True}
        assert infer_chart_type(section) == "change_bar"

    def test_no_dimensions_no_compare_returns_none(self):
        """빈 dimensions, compare_previous 없음 → none."""
        section = {"dimensions": [], "metrics": ["sessions"]}
        assert infer_chart_type(section) == "none"

    def test_dimensions_without_limit_returns_none(self):
        """dimensions 있지만 limit 없음 → none."""
        section = {"dimensions": ["country"], "metrics": ["sessions"]}
        assert infer_chart_type(section) == "none"

    def test_dimensions_with_limit_zero_returns_none(self):
        """dimensions + limit=0 → none (limit > 0 조건 미충족)."""
        section = {"dimensions": ["country"], "metrics": ["sessions"], "limit": 0}
        assert infer_chart_type(section) == "none"

    def test_date_with_limit_prioritizes_line(self):
        """dimensions에 date + limit이 동시에 있으면 line 우선."""
        section = {
            "dimensions": ["date", "sessionSource"],
            "metrics": ["sessions"],
            "limit": 10,
        }
        assert infer_chart_type(section) == "line"

    def test_empty_section_returns_none(self):
        """빈 섹션 데이터 → none."""
        assert infer_chart_type({}) == "none"


# ========== generate_custom_section 라우팅 테스트 ==========


class TestCustomSectionDispatch:
    """generate_custom_section() 차트 타입별 라우팅 테스트 (SVG 모드)."""

    def test_chart_type_none_skips(self, tmp_path):
        """chart_type=none이면 차트 생성 안 함."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {"chart_type": "none", "data": [{"x": 1}]}
        dispatcher.generate_custom_section("test_section", section_data)
        assert "test_section" not in dispatcher.manifest["charts"]

    def test_chart_type_horizontal_bar(self, tmp_path):
        """chart_type=horizontal_bar → 가로 막대 차트."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "horizontal_bar",
            "name": "테스트 섹션",
            "dimensions": ["pagePath"],
            "metrics": ["screenPageViews"],
            "data": [
                {"pagePath": "/home", "screenPageViews": 100},
                {"pagePath": "/about", "screenPageViews": 50},
            ],
        }
        dispatcher.generate_custom_section("custom_pages", section_data)
        assert "custom_pages" in dispatcher.manifest["charts"]
        assert os.path.exists(os.path.join(str(tmp_path), "custom_pages.svg"))

    def test_chart_type_line(self, tmp_path):
        """chart_type=line → 라인 차트 (SVG: vertical_bar로 폴백)."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "line",
            "name": "일별 전환",
            "dimensions": ["date"],
            "metrics": ["conversions"],
            "data": [
                {"date": "20260101", "conversions": 10},
                {"date": "20260102", "conversions": 15},
            ],
        }
        dispatcher.generate_custom_section("custom_trend", section_data)
        assert "custom_trend" in dispatcher.manifest["charts"]
        assert os.path.exists(os.path.join(str(tmp_path), "custom_trend.svg"))

    def test_chart_type_pie(self, tmp_path):
        """chart_type=pie → 파이 차트."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "pie",
            "name": "디바이스별 전환",
            "dimensions": ["deviceCategory"],
            "metrics": ["conversions"],
            "data": [
                {"deviceCategory": "desktop", "conversions": 100},
                {"deviceCategory": "mobile", "conversions": 80},
            ],
        }
        dispatcher.generate_custom_section("custom_device", section_data)
        assert "custom_device" in dispatcher.manifest["charts"]

    def test_chart_type_change_bar(self, tmp_path):
        """chart_type=change_bar → 변화율 차트."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "change_bar",
            "name": "전환 변화",
            "data": {
                "current": {"conversions": 120, "sessions": 1000},
                "previous": {"conversions": 100, "sessions": 900},
            },
        }
        dispatcher.generate_custom_section("custom_change", section_data)
        assert "custom_change" in dispatcher.manifest["charts"]

    def test_auto_infer_when_no_chart_type(self, tmp_path):
        """chart_type 미지정 → infer_chart_type() 자동 추론."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "name": "상위 검색어",
            "dimensions": ["searchTerm"],
            "metrics": ["sessions"],
            "limit": 10,
            "data": [
                {"searchTerm": "query1", "sessions": 50},
                {"searchTerm": "query2", "sessions": 30},
            ],
        }
        dispatcher.generate_custom_section("custom_search", section_data)
        # infer → horizontal_bar
        assert "custom_search" in dispatcher.manifest["charts"]

    def test_empty_data_skips(self, tmp_path):
        """데이터가 없으면 차트 생성 안 함."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "horizontal_bar",
            "dimensions": ["pagePath"],
            "metrics": ["screenPageViews"],
            "data": [],
        }
        dispatcher.generate_custom_section("empty_section", section_data)
        assert "empty_section" not in dispatcher.manifest["charts"]

    def test_chart_type_line_without_date_dimension(self, tmp_path):
        """chart_type=line이지만 date dimension이 없을 때 dimension 값을 라벨로 사용."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "line",
            "name": "소스별 추이",
            "dimensions": ["sessionSource"],
            "metrics": ["sessions"],
            "data": [
                {"sessionSource": "google", "sessions": 100},
                {"sessionSource": "direct", "sessions": 80},
            ],
        }
        dispatcher.generate_custom_section("custom_source_line", section_data)
        assert "custom_source_line" in dispatcher.manifest["charts"]
        assert os.path.exists(os.path.join(str(tmp_path), "custom_source_line.svg"))

    def test_chart_type_pie_all_zeros(self, tmp_path):
        """pie chart에서 모든 값이 0이면 에러 없이 처리."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "pie",
            "name": "빈 분포",
            "dimensions": ["deviceCategory"],
            "metrics": ["conversions"],
            "data": [
                {"deviceCategory": "desktop", "conversions": 0},
                {"deviceCategory": "mobile", "conversions": 0},
            ],
        }
        # ZeroDivisionError가 발생하지 않아야 함
        dispatcher.generate_custom_section("zero_pie", section_data)

    def test_unrecognized_chart_type_skips(self, tmp_path):
        """알 수 없는 chart_type이면 차트 생성을 건너뛰고 에러 없음."""
        dispatcher = ChartDispatcher(str(tmp_path), 'svg')
        section_data = {
            "chart_type": "unknown_type",
            "name": "알 수 없는 차트",
            "data": [{"x": 1}],
        }
        # 에러 없이 처리되어야 함
        dispatcher.generate_custom_section("unknown_chart", section_data)
        assert "unknown_chart" not in dispatcher.manifest["charts"]


# ========== 내장 섹션 핸들러 보존 테스트 ==========


class TestBuiltinSectionUnchanged:
    """기존 내장 섹션 핸들러가 정상 등록되어 있는지 확인."""

    def test_all_builtin_handlers_exist(self):
        """SECTION_HANDLERS의 모든 핸들러가 ChartDispatcher에 존재."""
        for section_id, handler_name in SECTION_HANDLERS.items():
            assert hasattr(ChartDispatcher, handler_name), (
                f"ChartDispatcher에 {handler_name} 메서드가 없습니다 (section: {section_id})"
            )

    def test_builtin_section_ids(self):
        """내장 섹션 ID 11개가 모두 존재."""
        expected = {
            'daily_trend', 'traffic_sources', 'campaigns', 'device',
            'top_pages', 'landing_pages', 'events', 'overview',
            'user_behavior', 'weekly_trend', 'weekly_comparison',
        }
        assert set(SECTION_HANDLERS.keys()) == expected
