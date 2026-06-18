from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class AnomalyRequest(BaseModel):
    target: str = "temperature"
    current_value: float
    recent_values: List[float] = Field(default_factory=list)
    threshold_z: float = 2.5


class ForecastRequest(BaseModel):
    target: str = "co2"
    recent_values: List[float]
    horizon_minutes: int = 15
    model_version: str = "linear_regression_numpy_v1"


class RiskRequest(BaseModel):
    target: str = "co2"
    predicted_value: float
    warning_threshold: float = 1000.0
    high_threshold: float = 1200.0



