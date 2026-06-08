from __future__ import annotations

import numpy as np
import pandas as pd


def add_time_features(df: pd.DataFrame, timestamp_col: str) -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out[timestamp_col])
    out['hour'] = ts.dt.hour + ts.dt.minute / 60.0
    out['day_of_week'] = ts.dt.dayofweek
    out['is_weekend'] = (ts.dt.dayofweek >= 5).astype(int)
    # Cyclical encoding: 23:00 and 00:00 are close in time, not far apart.
    out['sin_hour'] = np.sin(2 * np.pi * out['hour'] / 24.0)
    out['cos_hour'] = np.cos(2 * np.pi * out['hour'] / 24.0)
    return out


def make_supervised_forecasting_frame(
    df: pd.DataFrame,
    timestamp_col: str,
    target_col: str,
    horizon_steps: int,
    lags: list[int],
    rolling_windows: list[int],
) -> tuple[pd.DataFrame, list[str]]:
    """Create a tabular supervised dataset for forecasting.

    Row t contains only information available at time t or earlier.
    The target is value(t + horizon_steps).
    """
    out = df.copy()
    out[timestamp_col] = pd.to_datetime(out[timestamp_col])
    out = out.sort_values(timestamp_col).reset_index(drop=True)
    out = add_time_features(out, timestamp_col)

    out[f'{target_col}_current'] = out[target_col]
    for lag in lags:
        out[f'{target_col}_lag_{lag}'] = out[target_col].shift(lag)
    out[f'{target_col}_delta_1'] = out[target_col] - out[target_col].shift(1)
    for w in rolling_windows:
        # shift(1) avoids using the current target twice inside the rolling summary.
        shifted = out[target_col].shift(1)
        out[f'{target_col}_rolling_mean_{w}'] = shifted.rolling(w).mean()
        out[f'{target_col}_rolling_std_{w}'] = shifted.rolling(w).std()
        out[f'{target_col}_rolling_min_{w}'] = shifted.rolling(w).min()
        out[f'{target_col}_rolling_max_{w}'] = shifted.rolling(w).max()

    out['target_future'] = out[target_col].shift(-horizon_steps)

    ignore = {timestamp_col, 'target_future'}
    numeric_cols = [c for c in out.columns if c not in ignore and pd.api.types.is_numeric_dtype(out[c])]
    feature_cols = numeric_cols
    supervised = out[[timestamp_col] + feature_cols + ['target_future']].dropna().reset_index(drop=True)
    return supervised, feature_cols


def make_lstm_arrays(
    df: pd.DataFrame,
    timestamp_col: str,
    target_col: str,
    horizon_steps: int,
    sequence_length: int,
) -> tuple[np.ndarray, np.ndarray, list[pd.Timestamp], list[str]]:
    """Create sequence arrays for LSTM.

    X[i] = a window of length sequence_length ending at time t.
    y[i] = target at t + horizon_steps.
    """
    tmp = df.copy().sort_values(timestamp_col).reset_index(drop=True)
    tmp[timestamp_col] = pd.to_datetime(tmp[timestamp_col])
    tmp = add_time_features(tmp, timestamp_col)
    feature_cols = [c for c in tmp.columns if c != timestamp_col and pd.api.types.is_numeric_dtype(tmp[c])]
    values = tmp[feature_cols].astype(float).values
    target = tmp[target_col].astype(float).values
    timestamps = list(tmp[timestamp_col])

    X, y, ts_out = [], [], []
    last_start = len(tmp) - horizon_steps
    for end in range(sequence_length - 1, last_start):
        start = end - sequence_length + 1
        X.append(values[start:end+1])
        y.append(target[end + horizon_steps])
        ts_out.append(timestamps[end + horizon_steps])
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32), ts_out, feature_cols
