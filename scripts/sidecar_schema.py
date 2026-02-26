#!/usr/bin/env python3
"""
Smart Daily Briefing - JSON Sidecar 스키마 정의 및 검증기

v1.11.0에서 도입. 순수 Python 구현 (외부 의존성 없음).
브리핑 비교(v1.12.0)를 위해 diff-friendly 구조를 선제적으로 포함.
"""

SCHEMA_VERSION = "1.11"

# 합산(SUM) 메트릭: 기간 집계 시 단순 합산
SUM_METRICS = frozenset([
    "sessions", "totalUsers", "newUsers", "screenPageViews",
    "eventCount", "conversions", "transactions", "totalRevenue",
])

# 비율/평균 메트릭: 기간 집계 시 sessions 가중 평균
RATE_METRICS = frozenset([
    "bounceRate", "engagementRate", "averageSessionDuration",
    "sessionsPerUser", "screenPageViewsPerSession",
])

# 핵심 필수 필드 (없으면 검증 실패)
CRITICAL_FIELDS = frozenset({"date", "metrics"})

# 전체 필수 최상위 필드
REQUIRED_FIELDS = (
    "schema_version", "date", "preset", "date_range",
    "anomaly_threshold", "metrics", "anomalies", "insights",
    "comparable_keys",
)

# anomaly 엔트리 필수 필드
ANOMALY_REQUIRED = ("metric", "change_pct", "severity")

# insight 엔트리 필수 필드
INSIGHT_REQUIRED = ("severity", "text")

# severity 허용 값
VALID_SEVERITIES = frozenset({"info", "warning", "critical"})


def validate_sidecar(data):
    """Sidecar JSON 데이터를 검증한다.

    Args:
        data: dict — 파싱된 sidecar JSON

    Returns:
        (is_valid, warnings): bool과 경고 메시지 리스트.
        is_valid가 False면 필수 필드 누락 등 심각한 문제.
        warnings는 권장사항 위반 (is_valid=True여도 존재 가능).
    """
    warnings = []

    if not isinstance(data, dict):
        return False, ["sidecar 데이터가 dict가 아닙니다"]

    # 권장 필드 (없으면 경고만), 핵심 필드 (없으면 검증 실패)
    for field in REQUIRED_FIELDS:
        if field not in data:
            if field in CRITICAL_FIELDS:
                warnings.append(f"필수 필드 누락: {field}")
            else:
                warnings.append(f"권장 필드 누락: {field}")

    if any(f not in data for f in CRITICAL_FIELDS):
        return False, warnings

    # date 형식 (YYYY-MM-DD) — datetime.date.fromisoformat으로 실제 유효성 검증
    date_val = data.get("date", "")
    if isinstance(date_val, str) and date_val:
        try:
            from datetime import date as _date
            _date.fromisoformat(date_val)
        except (ValueError, TypeError):
            warnings.append(f"date 형식이 YYYY-MM-DD가 아닙니다: {date_val}")
    elif date_val is not None and not isinstance(date_val, str):
        warnings.append(f"date는 문자열이어야 합니다: {type(date_val).__name__}")

    # schema_version
    sv = data.get("schema_version")
    if sv is not None and not isinstance(sv, str):
        warnings.append(f"schema_version은 문자열이어야 합니다: {type(sv).__name__}")

    # anomaly_threshold
    threshold = data.get("anomaly_threshold")
    if threshold is not None and not isinstance(threshold, (int, float)):
        warnings.append(f"anomaly_threshold는 숫자여야 합니다: {type(threshold).__name__}")

    # metrics 검증
    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        warnings.append("metrics는 dict여야 합니다")
    else:
        for key, entry in metrics.items():
            if not isinstance(entry, dict):
                warnings.append(f"metrics.{key}는 dict여야 합니다")
                continue
            if "current" not in entry:
                warnings.append(f"metrics.{key}에 current 필드가 없습니다")
            for vk in ("current", "previous", "change_pct"):
                val = entry.get(vk)
                if val is not None and not isinstance(val, (int, float)):
                    warnings.append(
                        f"metrics.{key}.{vk}는 숫자 또는 null이어야 합니다"
                    )

    # anomalies 검증
    anomalies = data.get("anomalies", [])
    if not isinstance(anomalies, list):
        warnings.append("anomalies는 list여야 합니다")
    else:
        for i, entry in enumerate(anomalies):
            if not isinstance(entry, dict):
                warnings.append(f"anomalies[{i}]는 dict여야 합니다")
                continue
            for req in ANOMALY_REQUIRED:
                if req not in entry:
                    warnings.append(f"anomalies[{i}]에 {req} 필드가 없습니다")
            change_pct = entry.get("change_pct")
            if change_pct is not None and not isinstance(change_pct, (int, float)):
                warnings.append(
                    f"anomalies[{i}].change_pct는 숫자여야 합니다: {type(change_pct).__name__}"
                )
            sev = entry.get("severity")
            if sev is not None and sev not in VALID_SEVERITIES:
                warnings.append(
                    f"anomalies[{i}].severity가 유효하지 않습니다: {sev}"
                )

    # insights 검증
    insights = data.get("insights", [])
    if not isinstance(insights, list):
        warnings.append("insights는 list여야 합니다")
    else:
        for i, entry in enumerate(insights):
            if not isinstance(entry, dict):
                warnings.append(f"insights[{i}]는 dict여야 합니다")
                continue
            for req in INSIGHT_REQUIRED:
                if req not in entry:
                    warnings.append(f"insights[{i}]에 {req} 필드가 없습니다")
            sev = entry.get("severity")
            if sev is not None and sev not in VALID_SEVERITIES:
                warnings.append(
                    f"insights[{i}].severity가 유효하지 않습니다: {sev}"
                )

    # comparable_keys 검증
    comp_keys = data.get("comparable_keys")
    if comp_keys is not None:
        if not isinstance(comp_keys, list):
            warnings.append("comparable_keys는 list여야 합니다")
        else:
            for k in comp_keys:
                if not isinstance(k, str):
                    warnings.append(f"comparable_keys 항목은 문자열이어야 합니다: {k}")

    # top_sources, top_pages (선택적)
    for arr_key in ("top_sources", "top_pages"):
        arr = data.get(arr_key)
        if arr is not None and not isinstance(arr, list):
            warnings.append(f"{arr_key}는 list여야 합니다")

    has_critical = any("필수 필드 누락" in w for w in warnings)
    return not has_critical, warnings


def normalize_sidecar(data):
    """기존 v1.10.0 sidecar를 v1.11 형식으로 정규화한다.

    - schema_version 없으면 "1.0" 추가
    - comparable_keys 없으면 metrics 키 목록으로 자동 생성
    - metrics 내 문자열 값을 숫자로 변환 시도

    Args:
        data: dict — 파싱된 sidecar JSON (in-place 수정)

    Returns:
        정규화된 data dict
    """
    if not isinstance(data, dict):
        return data

    # schema_version 기본값
    if "schema_version" not in data:
        data["schema_version"] = "1.0"

    # comparable_keys 자동 생성
    if "comparable_keys" not in data:
        metrics = data.get("metrics", {})
        if isinstance(metrics, dict):
            data["comparable_keys"] = sorted(metrics.keys())
        else:
            data["comparable_keys"] = []

    # metrics 값 정규화: 문자열 → 숫자
    metrics = data.get("metrics", {})
    if isinstance(metrics, dict):
        for key, entry in metrics.items():
            if not isinstance(entry, dict):
                continue
            for vk in ("current", "previous", "change_pct"):
                val = entry.get(vk)
                if isinstance(val, str):
                    try:
                        entry[vk] = float(val)
                    except (ValueError, TypeError):
                        pass

    # anomalies, insights 기본값
    if "anomalies" not in data:
        data["anomalies"] = []
    if "insights" not in data:
        data["insights"] = []

    return data


def aggregate_sidecars(sidecars):
    """여러 일간 sidecar를 주간 단위로 집계한다.

    Args:
        sidecars: list[dict] — 일별 sidecar JSON 목록 (정규화 완료된 상태)

    Returns:
        dict — 집계된 metrics. 각 키에 대해:
            {"total": float, "daily_values": list, "avg": float}
    """
    if not sidecars:
        return {}

    # 모든 메트릭 키 수집
    all_keys = set()
    for s in sidecars:
        metrics = s.get("metrics", {})
        if isinstance(metrics, dict):
            all_keys.update(metrics.keys())

    result = {}
    for key in sorted(all_keys):
        values = []
        weights = []
        for s in sidecars:
            metrics = s.get("metrics", {})
            if not isinstance(metrics, dict):
                continue
            entry = metrics.get(key, {})
            if not isinstance(entry, dict):
                continue
            current = entry.get("current")
            if current is None:
                continue
            if not isinstance(current, (int, float)):
                continue
            values.append(current)
            # sessions를 가중치로 사용
            sess_entry = metrics.get("sessions", {})
            sess_val = sess_entry.get("current", 1) if isinstance(sess_entry, dict) else 1
            if not isinstance(sess_val, (int, float)) or sess_val <= 0:
                sess_val = 1
            weights.append(sess_val)

        if not values:
            continue

        if key in SUM_METRICS:
            total = sum(values)
            result[key] = {
                "total": total,
                "daily_values": values,
                "avg": total / len(values),
            }
        elif key in RATE_METRICS:
            # 비율/평균 메트릭: sessions 가중 평균
            weighted_sum = sum(v * w for v, w in zip(values, weights))
            weight_total = sum(weights)
            weighted_avg = weighted_sum / weight_total if weight_total > 0 else 0
            result[key] = {
                "weighted_avg": weighted_avg,
                "daily_values": values,
                "avg": weighted_avg,
            }
        else:
            # 알 수 없는 메트릭: SUM 방식으로 기본 처리
            total = sum(values)
            result[key] = {
                "total": total,
                "daily_values": values,
                "avg": total / len(values),
            }

    return result
