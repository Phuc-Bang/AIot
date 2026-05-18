from __future__ import annotations

from pathlib import Path
import time
from typing import Optional, List
import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI
from pydantic import BaseModel, Field

from utils import PROJECT_ROOT, MODEL_DIR, OUTPUT_DIR, FEATURE_COLUMNS, add_time_features

MODEL_PATH = MODEL_DIR / "isolation_forest_iforest_v1.joblib"
METRICS_PATH = OUTPUT_DIR / "iforest_metrics.json"

app = FastAPI(
    title="LAB 3 AIoT Anomaly Detection API",
    description="Demo deploy model anomaly detection: telemetry -> anomaly_score -> event -> decision",
    version="1.0.0"
)

model = None
if MODEL_PATH.exists():
    model = joblib.load(MODEL_PATH)


class TelemetryPoint(BaseModel):
    timestamp: str = Field(..., example="2013-07-05 09:00:00")
    value: float = Field(..., example=27.5)
    device_id: str = Field("nab_office_temp_sensor_01", example="room_temp_01")


class AnomalyRequest(BaseModel):
    history: List[TelemetryPoint] = Field(
        ...,
        description="Danh sách telemetry gần nhất. Nên gửi tối thiểu 36 điểm để rolling feature ổn định."
    )


def decision_from_score(score: float, zscore: float, delta: float) -> dict:
    if score >= 0.80:
        severity = "HIGH"
        decision = "CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK"
    elif score >= 0.55:
        severity = "MEDIUM"
        decision = "CREATE_WARNING_EVENT"
    else:
        severity = "LOW"
        decision = "LOG_FOR_MONITORING"

    reasons = []
    if abs(zscore) > 3:
        reasons.append("value deviates strongly from recent pattern")
    if abs(delta) > 3:
        reasons.append("sudden jump/drop compared with previous reading")
    if not reasons:
        reasons.append("model score indicates unusual pattern")

    return {
        "severity": severity,
        "decision": decision,
        "explanation": "; ".join(reasons),
        "safety_note": "Không tự động điều khiển thiết bị khi anomaly cao; cần xác nhận hoặc rule an toàn."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_path": str(MODEL_PATH),
    }


@app.get("/model-info")
def model_info():
    import json
    metrics = {}
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return {
        "model_name": "IsolationForest anomaly detector",
        "model_version": "iforest_v1",
        "input": "history of telemetry points with timestamp and value",
        "output": "anomaly_score, is_anomaly, severity, event_type, decision",
        "metrics": metrics
    }


@app.post("/detect-anomaly")
def detect_anomaly(payload: AnomalyRequest):
    if model is None:
        return {"error": "Model chưa được train. Hãy chạy: python src/train_anomaly.py"}

    start = time.time()
    df = pd.DataFrame([p.dict() for p in payload.history])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df = add_time_features(df)
    latest = df.iloc[[-1]].copy()

    raw_score = -model.named_steps["detector"].score_samples(
        model.named_steps["scaler"].transform(latest[FEATURE_COLUMNS])
    )[0]

    # Approximate normalization for API demo. In production, store training score distribution.
    score = float(1 / (1 + np.exp(-raw_score)))
    is_anomaly = score >= 0.55
    latest_row = latest.iloc[-1]
    decision = decision_from_score(
        score=score,
        zscore=float(latest_row.get("zscore_rolling", 0)),
        delta=float(latest_row.get("delta_1", 0))
    )

    return {
        "model_output": {
            "anomaly_score": round(score, 4),
            "is_anomaly": bool(is_anomaly),
            "model_version": "iforest_v1"
        },
        "event": {
            "event_type": "TEMPERATURE_ANOMALY" if is_anomaly else "NORMAL_TELEMETRY",
            "device_id": payload.history[-1].device_id,
            "timestamp": str(payload.history[-1].timestamp),
            "value": payload.history[-1].value,
            **decision
        },
        "api_check": {
            "latency_ms": round((time.time() - start) * 1000, 2),
            "input_points": len(payload.history)
        }
    }
