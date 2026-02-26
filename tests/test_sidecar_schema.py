"""sidecar_schema.py 스키마 검증 및 집계 테스트"""

import copy

import pytest

from sidecar_schema import (
    SCHEMA_VERSION,
    SUM_METRICS,
    RATE_METRICS,
    validate_sidecar,
    normalize_sidecar,
    aggregate_sidecars,
)


# ---------- Fixtures ----------

def _make_valid_sidecar(**overrides):
    """유효한 sidecar 기본 데이터 생성"""
    base = {
        "schema_version": SCHEMA_VERSION,
        "date": "2026-02-26",
        "preset": "default",
        "date_range": "7daysAgo",
        "anomaly_threshold": 20,
        "metrics": {
            "sessions": {"current": 7500, "previous": 6680, "change_pct": 12.3},
            "totalUsers": {"current": 5200, "previous": 4780, "change_pct": 8.8},
            "bounceRate": {"current": 0.42, "previous": 0.45, "change_pct": -6.7},
        },
        "anomalies": [
            {"metric": "averageSessionDuration", "change_pct": 21.9, "severity": "warning"}
        ],
        "insights": [
            {"severity": "info", "text": "모바일 트래픽이 54%로 증가"}
        ],
        "comparable_keys": ["bounceRate", "sessions", "totalUsers"],
        "top_sources": [
            {"source": "google/organic", "sessions": 1842, "share_pct": 45.2}
        ],
        "top_pages": [
            {"path": "/", "pageviews": 3421}
        ],
    }
    base.update(overrides)
    return base


# ---------- validate_sidecar 테스트 ----------

class TestValidateSidecar:
    """validate_sidecar() 함수 테스트"""

    def test_valid_sidecar_passes(self):
        data = _make_valid_sidecar()
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True
        assert len(warnings) == 0

    def test_missing_date_fails(self):
        data = _make_valid_sidecar()
        del data["date"]
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is False

    def test_missing_metrics_fails(self):
        data = _make_valid_sidecar()
        del data["metrics"]
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is False

    def test_missing_schema_version_warns(self):
        data = _make_valid_sidecar()
        del data["schema_version"]
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True  # schema_version은 경고만
        assert any("schema_version" in w for w in warnings)

    def test_missing_comparable_keys_warns(self):
        data = _make_valid_sidecar()
        del data["comparable_keys"]
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True
        assert any("comparable_keys" in w for w in warnings)

    def test_invalid_date_format_warns(self):
        data = _make_valid_sidecar(date="2026/02/26")
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True
        assert any("YYYY-MM-DD" in w for w in warnings)

    def test_metrics_entry_missing_current_warns(self):
        data = _make_valid_sidecar()
        data["metrics"]["sessions"] = {"previous": 6680, "change_pct": 12.3}
        is_valid, warnings = validate_sidecar(data)
        assert any("current" in w for w in warnings)

    def test_metrics_entry_string_value_warns(self):
        data = _make_valid_sidecar()
        data["metrics"]["sessions"]["current"] = "7500"
        is_valid, warnings = validate_sidecar(data)
        assert any("숫자 또는 null" in w for w in warnings)

    def test_anomaly_missing_severity_warns(self):
        data = _make_valid_sidecar()
        data["anomalies"] = [{"metric": "sessions", "change_pct": 25.0}]
        is_valid, warnings = validate_sidecar(data)
        assert any("severity" in w for w in warnings)

    def test_anomaly_invalid_severity_warns(self):
        data = _make_valid_sidecar()
        data["anomalies"] = [
            {"metric": "sessions", "change_pct": 25.0, "severity": "danger"}
        ]
        is_valid, warnings = validate_sidecar(data)
        assert any("유효하지 않습니다" in w for w in warnings)

    def test_insight_missing_text_warns(self):
        data = _make_valid_sidecar()
        data["insights"] = [{"severity": "info"}]
        is_valid, warnings = validate_sidecar(data)
        assert any("text" in w for w in warnings)

    def test_non_dict_input_fails(self):
        is_valid, warnings = validate_sidecar([1, 2, 3])
        assert is_valid is False

    def test_non_dict_input_string_fails(self):
        is_valid, warnings = validate_sidecar("not a dict")
        assert is_valid is False

    def test_empty_metrics_valid(self):
        """빈 metrics dict는 유효 (경고 없음)"""
        data = _make_valid_sidecar()
        data["metrics"] = {}
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True

    def test_null_previous_and_change_pct_valid(self):
        """previous와 change_pct가 null인 경우 유효"""
        data = _make_valid_sidecar()
        data["metrics"]["sessions"] = {"current": 7500, "previous": None, "change_pct": None}
        is_valid, warnings = validate_sidecar(data)
        assert is_valid is True
        assert len(warnings) == 0

    def test_non_string_comparable_keys_warns(self):
        data = _make_valid_sidecar()
        data["comparable_keys"] = ["sessions", 123]
        is_valid, warnings = validate_sidecar(data)
        assert any("문자열" in w for w in warnings)

    def test_top_sources_non_list_warns(self):
        data = _make_valid_sidecar()
        data["top_sources"] = "not a list"
        is_valid, warnings = validate_sidecar(data)
        assert any("top_sources" in w for w in warnings)


# ---------- normalize_sidecar 테스트 ----------

class TestNormalizeSidecar:
    """normalize_sidecar() 함수 테스트"""

    def test_adds_schema_version(self):
        data = {"date": "2026-02-26", "metrics": {}}
        result = normalize_sidecar(data)
        assert result["schema_version"] == "1.0"

    def test_preserves_existing_schema_version(self):
        data = {"schema_version": "1.11", "date": "2026-02-26", "metrics": {}}
        result = normalize_sidecar(data)
        assert result["schema_version"] == "1.11"

    def test_generates_comparable_keys(self):
        data = {
            "date": "2026-02-26",
            "metrics": {
                "sessions": {"current": 100},
                "bounceRate": {"current": 0.5},
            },
        }
        result = normalize_sidecar(data)
        assert result["comparable_keys"] == ["bounceRate", "sessions"]

    def test_converts_string_metrics_to_float(self):
        data = {
            "date": "2026-02-26",
            "metrics": {
                "sessions": {"current": "7500", "previous": "6680", "change_pct": "12.3"},
            },
        }
        result = normalize_sidecar(data)
        assert result["metrics"]["sessions"]["current"] == 7500.0
        assert result["metrics"]["sessions"]["previous"] == 6680.0
        assert result["metrics"]["sessions"]["change_pct"] == 12.3

    def test_adds_empty_anomalies(self):
        data = {"date": "2026-02-26", "metrics": {}}
        result = normalize_sidecar(data)
        assert result["anomalies"] == []

    def test_adds_empty_insights(self):
        data = {"date": "2026-02-26", "metrics": {}}
        result = normalize_sidecar(data)
        assert result["insights"] == []

    def test_non_dict_returns_as_is(self):
        result = normalize_sidecar("not a dict")
        assert result == "not a dict"

    def test_already_normalized_no_change(self):
        data = _make_valid_sidecar()
        original = copy.deepcopy(data)
        result = normalize_sidecar(data)
        assert result == original

    def test_unconvertible_string_stays(self):
        """변환 불가한 문자열은 그대로 유지"""
        data = {
            "date": "2026-02-26",
            "metrics": {"sessions": {"current": "N/A"}},
        }
        result = normalize_sidecar(data)
        assert result["metrics"]["sessions"]["current"] == "N/A"


# ---------- aggregate_sidecars 테스트 ----------

class TestAggregateSidecars:
    """aggregate_sidecars() 함수 테스트"""

    def _make_daily(self, date, sessions, bounce_rate):
        return {
            "schema_version": SCHEMA_VERSION,
            "date": date,
            "preset": "default",
            "date_range": "7daysAgo",
            "anomaly_threshold": 20,
            "metrics": {
                "sessions": {"current": sessions, "previous": None, "change_pct": None},
                "bounceRate": {"current": bounce_rate, "previous": None, "change_pct": None},
            },
            "anomalies": [],
            "insights": [],
            "comparable_keys": ["bounceRate", "sessions"],
        }

    def test_sum_metric_aggregation(self):
        sidecars = [
            self._make_daily("2026-02-20", 1000, 0.40),
            self._make_daily("2026-02-21", 1500, 0.35),
            self._make_daily("2026-02-22", 1200, 0.42),
        ]
        result = aggregate_sidecars(sidecars)
        assert result["sessions"]["total"] == 3700
        assert result["sessions"]["daily_values"] == [1000, 1500, 1200]

    def test_rate_metric_weighted_average(self):
        sidecars = [
            self._make_daily("2026-02-20", 1000, 0.40),
            self._make_daily("2026-02-21", 2000, 0.30),
        ]
        result = aggregate_sidecars(sidecars)
        # weighted avg: (0.40*1000 + 0.30*2000) / (1000+2000) = 1000/3000 = 0.3333...
        expected = (0.40 * 1000 + 0.30 * 2000) / 3000
        assert abs(result["bounceRate"]["total"] - expected) < 0.0001

    def test_empty_sidecars_returns_empty(self):
        result = aggregate_sidecars([])
        assert result == {}

    def test_skips_none_current_values(self):
        sidecar = {
            "metrics": {
                "sessions": {"current": None},
                "totalUsers": {"current": 100},
            },
        }
        result = aggregate_sidecars([sidecar])
        assert "sessions" not in result
        assert "totalUsers" in result

    def test_single_sidecar(self):
        sidecars = [self._make_daily("2026-02-20", 1000, 0.40)]
        result = aggregate_sidecars(sidecars)
        assert result["sessions"]["total"] == 1000
        assert result["bounceRate"]["total"] == 0.40

    def test_partial_metrics(self):
        """일부 sidecar에만 특정 메트릭이 있는 경우"""
        s1 = self._make_daily("2026-02-20", 1000, 0.40)
        s2 = self._make_daily("2026-02-21", 1500, 0.35)
        s2["metrics"]["newUsers"] = {"current": 500}
        result = aggregate_sidecars([s1, s2])
        assert "newUsers" in result
        assert result["newUsers"]["total"] == 500  # SUM 메트릭

    def test_seven_day_aggregation(self):
        """7일 전체 집계"""
        sidecars = [
            self._make_daily(f"2026-02-{20+i}", 1000 + i * 100, 0.40 - i * 0.01)
            for i in range(7)
        ]
        result = aggregate_sidecars(sidecars)
        expected_sessions = sum(1000 + i * 100 for i in range(7))
        assert result["sessions"]["total"] == expected_sessions
        assert len(result["sessions"]["daily_values"]) == 7
