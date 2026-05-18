from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error
from sklearn.neural_network import MLPRegressor

from utils import (
    PROJECT_ROOT, DATA_DIR, MODEL_DIR, OUTPUT_DIR, FEATURE_COLUMNS,
    load_dataset, add_time_features, time_split, build_events, evaluate_detection,
    make_windows, save_json
)

MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def train_isolation_forest() -> None:
    df = load_dataset()
    df = add_time_features(df)
    train_df, test_df = time_split(df, train_ratio=0.65)

    # Trong anomaly detection, ta ưu tiên học trên dữ liệu bình thường nếu có nhãn.
    train_normal = train_df[train_df["label"] == 0].copy()
    if len(train_normal) < 50:
        train_normal = train_df.copy()

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("detector", IsolationForest(
            n_estimators=200,
            contamination=0.04,
            random_state=42
        ))
    ])

    model.fit(train_normal[FEATURE_COLUMNS])

    # IsolationForest: score_samples càng thấp càng bất thường.
    raw_scores = -model.named_steps["detector"].score_samples(
        model.named_steps["scaler"].transform(test_df[FEATURE_COLUMNS])
    )
    # Chuẩn hóa score về khoảng 0-1 để dễ diễn giải trong AIoT.
    min_s, max_s = raw_scores.min(), raw_scores.max()
    anomaly_score = (raw_scores - min_s) / (max_s - min_s + 1e-9)
    threshold = np.quantile(anomaly_score, 0.92)
    test_df["anomaly_score"] = anomaly_score
    test_df["is_anomaly"] = (test_df["anomaly_score"] >= threshold).astype(int)
    test_df["model_version"] = "iforest_v1"

    metrics = evaluate_detection(test_df["label"], test_df["is_anomaly"])
    metrics["threshold"] = float(round(threshold, 4))
    metrics["train_rows"] = int(len(train_df))
    metrics["test_rows"] = int(len(test_df))
    metrics["model_type"] = "IsolationForest"
    metrics["note"] = "Precision/Recall/F1 chỉ có ý nghĩa khi label anomaly có sẵn."

    joblib.dump(model, MODEL_DIR / "isolation_forest_iforest_v1.joblib")
    save_json(metrics, OUTPUT_DIR / "iforest_metrics.json")
    test_df.to_csv(OUTPUT_DIR / "iforest_test_predictions.csv", index=False)

    events = build_events(test_df)
    events.to_csv(OUTPUT_DIR / "anomaly_event_log.csv", index=False)

    print("=== Isolation Forest metrics ===")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Đã lưu model: {MODEL_DIR / 'isolation_forest_iforest_v1.joblib'}")
    print(f"Đã lưu event log: {OUTPUT_DIR / 'anomaly_event_log.csv'}")


def train_neural_autoencoder_demo(window_size: int = 24) -> None:
    """Optional neural-network demo with sklearn MLPRegressor.

    Đây không phải LSTM. Mục tiêu là giúp sinh viên hiểu ý tưởng autoencoder:
    input window -> reconstructed window -> reconstruction MSE -> anomaly_score.
    """
    df = add_time_features(load_dataset())
    train_df, test_df = time_split(df, train_ratio=0.65)

    train_normal_values = train_df.loc[train_df["label"] == 0, "value"].values
    if len(train_normal_values) < window_size + 10:
        train_normal_values = train_df["value"].values

    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train_normal_values.reshape(-1, 1)).ravel()
    test_scaled = scaler.transform(test_df["value"].values.reshape(-1, 1)).ravel()

    X_train = make_windows(train_scaled, window_size=window_size)
    X_test = make_windows(test_scaled, window_size=window_size)

    # Autoencoder đơn giản: mô hình học tái tạo chính input window.
    ae = MLPRegressor(
        hidden_layer_sizes=(12, 4, 12),
        activation="relu",
        solver="adam",
        max_iter=150,
        random_state=42,
        early_stopping=True,
        n_iter_no_change=20
    )
    ae.fit(X_train, X_train)
    reconstructed = ae.predict(X_test)
    reconstruction_mse = ((X_test - reconstructed) ** 2).mean(axis=1)

    threshold = np.quantile(reconstruction_mse, 0.92)
    pred = (reconstruction_mse >= threshold).astype(int)

    # Align labels to end of each window.
    aligned = test_df.iloc[window_size-1:].copy().reset_index(drop=True)
    aligned["reconstruction_mse"] = reconstruction_mse
    aligned["is_anomaly_ae"] = pred

    metrics = evaluate_detection(aligned["label"], aligned["is_anomaly_ae"])
    metrics["threshold_mse"] = float(round(threshold, 6))
    metrics["model_type"] = "MLPRegressor Autoencoder demo"
    metrics["window_size"] = int(window_size)
    metrics["mse_mean"] = float(round(float(reconstruction_mse.mean()), 6))
    metrics["mse_max"] = float(round(float(reconstruction_mse.max()), 6))
    metrics["note"] = "MSE cao nghĩa là model tái tạo window kém, có khả năng bất thường."

    joblib.dump({"scaler": scaler, "autoencoder": ae, "window_size": window_size, "threshold": threshold},
                MODEL_DIR / "mlp_autoencoder_demo.joblib")
    save_json(metrics, OUTPUT_DIR / "autoencoder_metrics.json")
    aligned.to_csv(OUTPUT_DIR / "autoencoder_test_predictions.csv", index=False)

    print("=== Neural Autoencoder demo metrics ===")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    train_isolation_forest()
    train_neural_autoencoder_demo()
