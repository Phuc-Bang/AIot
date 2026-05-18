from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.data_utils import API_FEATURES, RAW_FEATURES, compute_anomaly_score, decision_from_outputs, load_model_bundle

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Lab 2 AIoT Occupancy Baseline Inference API",
    description="Demo deploy model cơ bản: telemetry -> model output -> decision/command hint.",
    version="lab2-v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_BUNDLE = load_model_bundle()
MODEL = MODEL_BUNDLE["model"]
TRAIN_STATS = MODEL_BUNDLE["train_stats"]
METRICS = MODEL_BUNDLE.get("metrics", {})


class TelemetryInput(BaseModel):
    room_id: str = Field(default="room_101")
    device_id: str = Field(default="env_node_01")
    timestamp: Optional[str] = Field(default=None, description="ISO datetime, e.g. 2015-02-05 09:30:00")
    Temperature: float = Field(..., ge=-20, le=80)
    Humidity: float = Field(..., ge=0, le=100)
    Light: float = Field(..., ge=0)
    CO2: float = Field(..., ge=250)
    HumidityRatio: float = Field(..., ge=0)


@app.get("/dashboard")
def get_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return FileResponse(dashboard_path)


@app.get("/")
def root():
    return {
        "message": "Lab 2 AIoT model deployment demo is running.",
        "try": ["/health", "/model-info", "/docs", "/predict"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_version": MODEL_BUNDLE.get("model_version", "unknown"),
    }


@app.get("/model-info")
def model_info():
    return {
        "model_name": MODEL_BUNDLE.get("model_name"),
        "model_version": MODEL_BUNDLE.get("model_version"),
        "feature_cols": MODEL_BUNDLE.get("feature_cols"),
        "metrics": METRICS,
        "decision_outputs": [
            "CHECK_SENSOR_OR_DATA",
            "ALERT_VENTILATION_AND_TURN_FAN_ON",
            "ROOM_OCCUPIED_LIGHTING_NEEDED",
            "ROOM_OCCUPIED_KEEP_COMFORT_MODE",
            "ROOM_EMPTY_SAVE_ENERGY",
        ],
    }


def build_feature_row(payload: TelemetryInput) -> pd.DataFrame:
    ts = pd.to_datetime(payload.timestamp) if payload.timestamp else pd.Timestamp(datetime.now())
    row = {
        "Temperature": payload.Temperature,
        "Humidity": payload.Humidity,
        "Light": payload.Light,
        "CO2": payload.CO2,
        "HumidityRatio": payload.HumidityRatio,
        "hour": int(ts.hour),
        "dayofweek": int(ts.dayofweek),
    }
    return pd.DataFrame([row])


@app.post("/predict")
def predict(payload: TelemetryInput):
    features = build_feature_row(payload)
    probability = float(MODEL.predict_proba(features[API_FEATURES])[:, 1][0])
    anomaly_score = float(compute_anomaly_score(features[RAW_FEATURES], TRAIN_STATS)[0])
    decision = decision_from_outputs(
        occupancy_probability=probability,
        anomaly_score=anomaly_score,
        co2=payload.CO2,
        light=payload.Light,
    )
    return {
        "input": payload.model_dump(),
        "model_output": {
            "occupancy_probability": round(probability, 4),
            "predicted_occupancy": decision["predicted_occupancy"],
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": decision["is_anomaly"],
        },
        "decision": {
            "decision": decision["decision"],
            "command_hint": decision["command_hint"],
            "safety_note": decision["safety_note"],
        },
    }
