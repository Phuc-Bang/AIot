from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

pred_file = OUT / "iforest_test_predictions.csv"
if not pred_file.exists():
    raise FileNotFoundError("Run python src/train_anomaly.py first")

df = pd.read_csv(pred_file)
df["timestamp"] = pd.to_datetime(df["timestamp"])

plt.figure(figsize=(12, 5))
plt.plot(df["timestamp"], df["value"], label="temperature")
anom = df[df["is_anomaly"] == 1]
plt.scatter(anom["timestamp"], anom["value"], label="detected anomaly")
plt.title("LAB 3 - Time-series anomaly detection result")
plt.xlabel("timestamp")
plt.ylabel("value")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "anomaly_detection_result.png", dpi=160)
plt.close()

plt.figure(figsize=(12, 4))
plt.plot(df["timestamp"], df["anomaly_score"], label="anomaly_score")
plt.title("Anomaly score over time")
plt.xlabel("timestamp")
plt.ylabel("score")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "anomaly_score_over_time.png", dpi=160)
plt.close()

print("Saved figures to", FIG)
