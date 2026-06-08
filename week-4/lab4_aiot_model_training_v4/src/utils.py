from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd


def safe_mape(y_true, y_pred, eps: float = 1e-8) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.maximum(np.abs(y_true), eps)
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)


def regression_metrics(y_true, y_pred) -> Dict[str, float]:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        'mae': float(mean_absolute_error(y_true, y_pred)),
        'rmse': float(math.sqrt(mean_squared_error(y_true, y_pred))),
        'mape': safe_mape(y_true, y_pred),
        'r2': float(r2_score(y_true, y_pred)),
        'bias_pred_minus_actual': float(np.mean(y_pred - y_true)),
    }


def chronological_split(df: pd.DataFrame, train_ratio: float = 0.60, val_ratio: float = 0.20):
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()
    return train, val, test


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def print_header(text: str) -> None:
    print('\n' + '=' * 80)
    print(text)
    print('=' * 80)
