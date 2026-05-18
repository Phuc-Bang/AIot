from __future__ import annotations

import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "ambient_temperature_system_failure_labeled.csv"
if not DATA_FILE.exists():
    DATA_FILE = ROOT / "data" / "sample_ambient_temperature_system_failure.csv"

df = pd.read_csv(DATA_FILE).tail(40)
history = [
    {"timestamp": str(row["timestamp"]), "value": float(row["value"]), "device_id": "nab_office_temp_sensor_01"}
    for _, row in df.iterrows()
]

print("Kiểm tra /health")
print(requests.get("http://127.0.0.1:8000/health", timeout=10).json())

print("\nKiểm tra /model-info")
print(requests.get("http://127.0.0.1:8000/model-info", timeout=10).json())

print("\nKiểm tra /detect-anomaly")
resp = requests.post("http://127.0.0.1:8000/detect-anomaly", json={"history": history}, timeout=10)
print(resp.json())
