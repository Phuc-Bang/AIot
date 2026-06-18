from __future__ import annotations

import math
from statistics import mean, stdev
from typing import List, Dict, Any

import numpy as np

# ---------------------------------------------------------------------------
# ML-based models (numpy-only, no scikit-learn/scipy dependency)
# ---------------------------------------------------------------------------


def detect_anomaly_ml(current_value: float, recent_values: List[float], threshold_z: float = 2.5) -> Dict[str, Any]:
    """Anomaly detection using modified Z-score with MAD (robust statistics).

    Uses Median Absolute Deviation which is more robust to outliers than
    standard z-score. Falls back to standard z-score if not enough data.
    """
    if len(recent_values) < 4:
        return detect_anomaly_rule(current_value, recent_values, threshold_z)

    arr = np.array(recent_values, dtype=np.float64)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median))) or 1e-6
    modified_z = abs((current_value - median) / (1.4826 * mad))

    is_anomaly = modified_z >= threshold_z
    score = modified_z

    if not is_anomaly:
        severity = "NORMAL"
        decision = "NO_ALERT"
        explanation = f"Modified Z-score={score:.4f}, median={median:.3f}, MAD={mad:.4f}"
    elif score < threshold_z * 1.5:
        severity = "WARNING"
        decision = "CREATE_WARNING_EVENT"
        explanation = f"Modified Z-score={score:.4f}, mild anomaly detected"
    else:
        severity = "HIGH"
        decision = "CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK"
        explanation = f"Modified Z-score={score:.4f}, strong anomaly detected"

    return {
        "model_output": {
            "anomaly_score": round(float(score), 6),
            "threshold_used": threshold_z,
            "is_anomaly": bool(is_anomaly),
            "model_version": "modified_zscore_mad_v1"
        },
        "event": {
            "severity": severity,
            "decision": decision,
            "explanation": explanation,
            "safety_note": "Không tự động điều khiển thiết bị chỉ dựa trên một điểm anomaly."
        }
    }


def forecast_ml(recent_values: List[float], horizon_minutes: int = 15) -> Dict[str, Any]:
    """Forecast using least-squares linear regression (numpy polyfit).

    Fits a degree-1 polynomial to the time series and predicts the next value.
    Falls back to moving average if not enough data.
    """
    if len(recent_values) < 3:
        return forecast_moving_average(recent_values, horizon_minutes)

    n = len(recent_values)
    X = np.arange(n, dtype=np.float64)
    y = np.array(recent_values, dtype=np.float64)

    coeffs = np.polyfit(X, y, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])

    predicted = slope * n + intercept
    last_value = recent_values[-1]
    delta = predicted - last_value

    y_pred = slope * X + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 1.0

    return {
        "model_output": {
            "predicted_value": round(float(predicted), 6),
            "last_value": round(float(last_value), 6),
            "forecast_delta": round(float(delta), 6),
            "forecast_horizon_minutes": horizon_minutes,
            "model_version": "linear_regression_numpy_v1",
            "regression_metrics": {
                "slope": round(slope, 4),
                "intercept": round(intercept, 4),
                "r2_score": round(r2, 4)
            }
        },
        "evaluation_hint": {
            "note": "Linear regression via numpy polyfit (no scikit-learn dependency)."
        }
    }


# ---------------------------------------------------------------------------
# Original rule-based functions (kept as fallbacks)
# ---------------------------------------------------------------------------


def detect_anomaly_rule(current_value: float, recent_values: List[float], threshold_z: float = 2.5) -> Dict[str, Any]:
    """Simple fallback anomaly logic."""
    if len(recent_values) < 3:
        score = 0.0
        is_anomaly = False
        explanation = "Not enough recent history; using safe fallback."
    else:
        mu = mean(recent_values)
        sigma = stdev(recent_values) or 1e-6
        score = abs((current_value - mu) / sigma)
        is_anomaly = score >= threshold_z
        explanation = f"z-score={score:.3f}, mean={mu:.3f}, std={sigma:.3f}"

    if not is_anomaly:
        severity = "NORMAL"
        decision = "NO_ALERT"
    elif score < threshold_z * 1.5:
        severity = "WARNING"
        decision = "CREATE_WARNING_EVENT"
    else:
        severity = "HIGH"
        decision = "CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK"

    return {
        "model_output": {
            "anomaly_score": round(float(score), 6),
            "threshold_used": threshold_z,
            "is_anomaly": bool(is_anomaly),
            "model_version": "zscore_fallback_v1"
        },
        "event": {
            "severity": severity,
            "decision": decision,
            "explanation": explanation,
            "safety_note": "Không tự động điều khiển thiết bị chỉ dựa trên một điểm anomaly."
        }
    }


def forecast_moving_average(recent_values: List[float], horizon_minutes: int = 15) -> Dict[str, Any]:
    if not recent_values:
        raise ValueError("recent_values must not be empty")
    window = recent_values[-min(5, len(recent_values)):]
    predicted = sum(window) / len(window)
    last_value = recent_values[-1]
    delta = predicted - last_value
    return {
        "model_output": {
            "predicted_value": round(float(predicted), 6),
            "last_value": round(float(last_value), 6),
            "forecast_delta": round(float(delta), 6),
            "forecast_horizon_minutes": horizon_minutes,
            "model_version": "moving_average_baseline_v1"
        },
        "evaluation_hint": {
            "note": "Simple moving average fallback."
        }
    }


def risk_from_forecast(predicted_value: float, warning_threshold: float, high_threshold: float) -> Dict[str, Any]:
    if predicted_value >= high_threshold:
        risk_level = "HIGH"
        recommendation = "REQUIRE_HUMAN_CHECK_BEFORE_ACTUATOR_CONTROL"
    elif predicted_value >= warning_threshold:
        risk_level = "WARNING"
        recommendation = "IMPROVE_MONITORING_OR_PREPARE_ACTION"
    else:
        risk_level = "NORMAL"
        recommendation = "CONTINUE_MONITORING"
    return {
        "decision": {
            "risk_level": risk_level,
            "recommendation": recommendation,
            "safety_note": "Forecast output must pass decision and safety rules before controlling devices."
        }
    }
