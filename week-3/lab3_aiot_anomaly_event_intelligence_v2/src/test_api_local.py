from __future__ import annotations

"""Test API logic without starting uvicorn.

Use this when the classroom machine blocks local ports or when students want to verify
that app.py can load the model and return the correct response schema.
"""

import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from app import app

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "ambient_temperature_system_failure_labeled.csv"
if not DATA_FILE.exists():
    DATA_FILE = ROOT / "data" / "sample_ambient_temperature_system_failure.csv"

df = pd.read_csv(DATA_FILE).tail(40)
history = [
    {"timestamp": str(row["timestamp"]), "value": float(row["value"]), "device_id": "nab_office_temp_sensor_01"}
    for _, row in df.iterrows()
]

client = TestClient(app)

print("Kiểm tra /health")
print(client.get("/health").json())

print("\nKiểm tra /model-info")
print(client.get("/model-info").json())

print("\nKiểm tra /detect-anomaly")
resp = client.post("/detect-anomaly", json={"history": history})
print(resp.status_code)
print(resp.json())

assert resp.status_code == 200
data = resp.json()
assert "model_output" in data
assert "event" in data
assert "anomaly_score" in data["model_output"]
assert "decision" in data["event"]
print("\nPASS: API response schema hợp lệ.")
