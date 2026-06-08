from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import DATASET_CONFIGS, DATA_PROCESSED, MODELS, OUTPUTS
from feature_engineering import make_supervised_forecasting_frame
from utils import chronological_split, print_header, regression_metrics, save_json


def evaluate_model_record(dataset_key, model_name, split, y_true, y_pred, params=None):
    metrics = regression_metrics(y_true, y_pred)
    row = {
        'dataset': dataset_key,
        'model': model_name,
        'split': split,
        **metrics,
        'params': json.dumps(params or {}, ensure_ascii=False),
    }
    return row


def fit_and_predict_classical(X_train, y_train, X_val, X_test, random_state=42):
    models = {
        'LinearRegression': Pipeline([('scaler', StandardScaler()), ('model', LinearRegression())]),
        'Ridge_alpha_1': Pipeline([('scaler', StandardScaler()), ('model', Ridge(alpha=1.0, random_state=random_state))]),
        'RandomForest_default': RandomForestRegressor(n_estimators=60, max_depth=8, min_samples_leaf=2, random_state=random_state, n_jobs=-1),
        'GradientBoosting_advanced': GradientBoostingRegressor(n_estimators=70, learning_rate=0.06, max_depth=3, random_state=random_state),
    }
    fitted = {}
    preds = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        fitted[name] = model
        preds[name] = {'val': model.predict(X_val), 'test': model.predict(X_test)}
    return fitted, preds


def tune_random_forest(X_train, y_train, X_val, y_val, dataset_key):
    grid = [
        {'n_estimators': 30, 'max_depth': 5, 'min_samples_leaf': 2},
        {'n_estimators': 60, 'max_depth': 8, 'min_samples_leaf': 2},
        {'n_estimators': 80, 'max_depth': 12, 'min_samples_leaf': 2},
        {'n_estimators': 80, 'max_depth': None, 'min_samples_leaf': 3},
    ]
    rows = []
    best = None
    for params in grid:
        model = RandomForestRegressor(**params, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        pred_val = model.predict(X_val)
        m = regression_metrics(y_val, pred_val)
        row = {'dataset': dataset_key, 'model': 'RandomForest_tuned_candidate', **params, **{f'val_{k}': v for k, v in m.items()}}
        rows.append(row)
        if best is None or m['mae'] < best[0]:
            best = (m['mae'], params, model)
    return rows, best[1], best[2]


def write_model_card(dataset_key, config, best_row, feature_importance_path):
    card = f"""# Model card - {config['display_name']}

## Bài toán
- Target: `{config['target']}`
- Forecast horizon: {config['horizon_minutes']} phút
- Đơn vị: {config['unit']}

## Model tốt nhất theo validation MAE
- Model: {best_row['model']}
- Test MAE: {best_row['mae']:.4f}
- Test RMSE: {best_row['rmse']:.4f}
- Test MAPE: {best_row['mape']:.2f}%
- Test R2: {best_row['r2']:.4f}
- Bias pred-actual: {best_row['bias_pred_minus_actual']:.4f}

## Cách đọc nhanh
- MAE cho biết trung bình model lệch bao nhiêu đơn vị.
- RMSE nhạy với các lỗi lớn. Nếu RMSE cao hơn MAE nhiều, có một số thời điểm model sai mạnh.
- Bias dương nghĩa là model có xu hướng dự báo cao hơn thực tế. Bias âm nghĩa là model dự báo thấp hơn thực tế.

## Feature importance
Xem file: `{feature_importance_path}`.

## Câu hỏi sinh viên phải trả lời
1. Model tốt nhất có hơn Last Value baseline nhiều không?
2. Nếu không hơn nhiều, lý do có thể là gì?
3. Feature nào quan trọng nhất? Feature đó có hợp lý về mặt IoT không?
4. Có giai đoạn nào model sai nhiều hơn bình thường không?
5. Với sai số hiện tại, model có đủ an toàn để điều khiển thiết bị tự động không?
"""
    path = OUTPUTS / f'model_card_{dataset_key}.md'
    path.write_text(card, encoding='utf-8')


def run_dataset(dataset_key: str, config: dict):
    print_header(f'Training classical models for {dataset_key}')
    path = config['processed_file']
    if not path.exists():
        raise FileNotFoundError(f'{path} not found. Run python src/prepare_datasets.py first.')
    raw = pd.read_csv(path)
    supervised, feature_cols = make_supervised_forecasting_frame(
        raw,
        timestamp_col=config['timestamp'],
        target_col=config['target'],
        horizon_steps=config['horizon_steps'],
        lags=config['lags'],
        rolling_windows=config['rolling_windows'],
    )
    train, val, test = chronological_split(supervised)
    X_train, y_train = train[feature_cols], train['target_future']
    X_val, y_val = val[feature_cols], val['target_future']
    X_test, y_test = test[feature_cols], test['target_future']

    rows = []
    pred_df = test[[config['timestamp'], 'target_future']].rename(columns={'target_future': 'actual'}).copy()

    # Baselines: no ML, only current value or rolling average.
    baseline_last_val = val[f"{config['target']}_current"].values
    baseline_last_test = test[f"{config['target']}_current"].values
    baseline_ma_col = f"{config['target']}_rolling_mean_{config['rolling_windows'][0]}"
    baseline_ma_val = val[baseline_ma_col].values
    baseline_ma_test = test[baseline_ma_col].values
    rows.append(evaluate_model_record(dataset_key, 'LastValue_baseline', 'val', y_val, baseline_last_val))
    rows.append(evaluate_model_record(dataset_key, 'LastValue_baseline', 'test', y_test, baseline_last_test))
    rows.append(evaluate_model_record(dataset_key, 'MovingAverage_baseline', 'val', y_val, baseline_ma_val))
    rows.append(evaluate_model_record(dataset_key, 'MovingAverage_baseline', 'test', y_test, baseline_ma_test))
    pred_df['pred_LastValue_baseline'] = baseline_last_test
    pred_df['pred_MovingAverage_baseline'] = baseline_ma_test

    # ML models.
    fitted, preds = fit_and_predict_classical(X_train, y_train, X_val, X_test)
    for name, p in preds.items():
        rows.append(evaluate_model_record(dataset_key, name, 'val', y_val, p['val']))
        rows.append(evaluate_model_record(dataset_key, name, 'test', y_test, p['test']))
        pred_df[f'pred_{name}'] = p['test']

    tuning_rows, best_rf_params, best_rf_model = tune_random_forest(X_train, y_train, X_val, y_val, dataset_key)
    rf_val = best_rf_model.predict(X_val)
    rf_test = best_rf_model.predict(X_test)
    rows.append(evaluate_model_record(dataset_key, 'RandomForest_tuned', 'val', y_val, rf_val, best_rf_params))
    rows.append(evaluate_model_record(dataset_key, 'RandomForest_tuned', 'test', y_test, rf_test, best_rf_params))
    pred_df['pred_RandomForest_tuned'] = rf_test
    fitted['RandomForest_tuned'] = best_rf_model

    metrics_df = pd.DataFrame(rows)
    val_df = metrics_df[metrics_df['split'] == 'val'].sort_values('mae')
    best_name = val_df.iloc[0]['model']
    best_model = fitted.get(best_name)
    if best_model is None:
        # Best can be a baseline; for deployment model card, choose best trainable ML model.
        ml_val_df = val_df[~val_df['model'].str.contains('baseline')]
        best_name = ml_val_df.iloc[0]['model']
        best_model = fitted[best_name]

    # Save best model bundle.
    bundle = {
        'dataset_key': dataset_key,
        'display_name': config['display_name'],
        'target': config['target'],
        'timestamp_col': config['timestamp'],
        'horizon_steps': config['horizon_steps'],
        'horizon_minutes': config['horizon_minutes'],
        'feature_cols': feature_cols,
        'model_name': best_name,
        'model': best_model,
    }
    joblib.dump(bundle, MODELS / f'{dataset_key}_best_model.joblib')

    # Feature importance for tree models.
    fi_rows = []
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        fi_rows = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    elif hasattr(best_model, 'named_steps') and hasattr(best_model.named_steps.get('model'), 'coef_'):
        coefs = np.ravel(best_model.named_steps['model'].coef_)
        fi_rows = sorted(zip(feature_cols, np.abs(coefs)), key=lambda x: x[1], reverse=True)
    fi_df = pd.DataFrame(fi_rows, columns=['feature', 'importance'])
    fi_path = OUTPUTS / f'feature_importance_{dataset_key}.csv'
    fi_df.to_csv(fi_path, index=False)

    pred_path = OUTPUTS / f'predictions_{dataset_key}.csv'
    pred_df.to_csv(pred_path, index=False)
    print(f'Saved predictions: {pred_path}')

    # Model card based on the chosen trainable model's test row.
    best_test_row = metrics_df[(metrics_df['split'] == 'test') & (metrics_df['model'] == best_name)].iloc[0]
    write_model_card(dataset_key, config, best_test_row, fi_path.relative_to(OUTPUTS.parent))
    return metrics_df, pd.DataFrame(tuning_rows), pred_path


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    all_metrics = []
    all_tuning = []
    for dataset_key, config in DATASET_CONFIGS.items():
        metrics, tuning, _ = run_dataset(dataset_key, config)
        all_metrics.append(metrics)
        all_tuning.append(tuning)
    metrics_df = pd.concat(all_metrics, ignore_index=True)
    tuning_df = pd.concat(all_tuning, ignore_index=True)
    metrics_df.to_csv(OUTPUTS / 'metrics_all_models.csv', index=False)
    tuning_df.to_csv(OUTPUTS / 'tuning_log.csv', index=False)

    # Comparison table: validation winner and test metrics.
    comps = []
    for dataset_key in DATASET_CONFIGS:
        subset = metrics_df[metrics_df['dataset'] == dataset_key]
        best_val = subset[subset['split'] == 'val'].sort_values('mae').iloc[0]
        best_test = subset[(subset['split'] == 'test') & (subset['model'] == best_val['model'])].iloc[0]
        baseline_test = subset[(subset['split'] == 'test') & (subset['model'] == 'LastValue_baseline')].iloc[0]
        comps.append({
            'dataset': dataset_key,
            'best_model_by_val_mae': best_val['model'],
            'best_model_test_mae': best_test['mae'],
            'last_value_test_mae': baseline_test['mae'],
            'mae_improvement_vs_last_value_percent': (baseline_test['mae'] - best_test['mae']) / max(baseline_test['mae'], 1e-8) * 100.0,
            'best_model_test_rmse': best_test['rmse'],
            'best_model_test_mape': best_test['mape'],
            'best_model_test_r2': best_test['r2'],
        })
    pd.DataFrame(comps).to_csv(OUTPUTS / 'model_comparison.csv', index=False)
    save_json(OUTPUTS / 'classical_training_summary.json', comps)
    print_header('Training completed')
    print(metrics_df[['dataset','model','split','mae','rmse','mape','r2','bias_pred_minus_actual']].to_string(index=False))


if __name__ == '__main__':
    main()
