from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt

from config import DATASET_CONFIGS, OUTPUTS, FIGURES


def find_best_prediction_column(dataset_key: str) -> str:
    comp = pd.read_csv(OUTPUTS / 'model_comparison.csv')
    best_name = comp.loc[comp['dataset'] == dataset_key, 'best_model_by_val_mae'].iloc[0]
    return 'pred_' + best_name


def plot_forecast_vs_actual(dataset_key: str):
    df = pd.read_csv(OUTPUTS / f'predictions_{dataset_key}.csv')
    config = DATASET_CONFIGS[dataset_key]
    best_col = find_best_prediction_column(dataset_key)
    # Keep the chart readable.
    view = df.tail(min(350, len(df))).copy()
    plt.figure(figsize=(11, 4.5))
    plt.plot(pd.to_datetime(view[config['timestamp']]), view['actual'], label='actual')
    plt.plot(pd.to_datetime(view[config['timestamp']]), view[best_col], label=best_col.replace('pred_', 'predicted: '))
    plt.xlabel('time')
    plt.ylabel(f"{config['target']} ({config['unit']})")
    plt.title(f"Forecast vs actual - {dataset_key}")
    plt.legend()
    plt.tight_layout()
    out = FIGURES / f'forecast_vs_actual_{dataset_key}.png'
    plt.savefig(out, dpi=160)
    plt.close()


def plot_error_over_time(dataset_key: str):
    df = pd.read_csv(OUTPUTS / f'predictions_{dataset_key}.csv')
    config = DATASET_CONFIGS[dataset_key]
    best_col = find_best_prediction_column(dataset_key)
    df['error'] = df[best_col] - df['actual']
    view = df.tail(min(500, len(df))).copy()
    plt.figure(figsize=(11, 4.5))
    plt.plot(pd.to_datetime(view[config['timestamp']]), view['error'], label='prediction error')
    plt.axhline(0, linestyle='--', linewidth=1)
    plt.xlabel('time')
    plt.ylabel('predicted - actual')
    plt.title(f'Error over time - {dataset_key}')
    plt.legend()
    plt.tight_layout()
    out = FIGURES / f'error_over_time_{dataset_key}.png'
    plt.savefig(out, dpi=160)
    plt.close()


def plot_metric_comparison():
    metrics = pd.read_csv(OUTPUTS / 'metrics_all_models.csv')
    test = metrics[metrics['split'] == 'test'].copy()
    # Use a compact chart: one per dataset, MAE values for all models.
    for dataset_key in DATASET_CONFIGS:
        sub = test[test['dataset'] == dataset_key].sort_values('mae')
        plt.figure(figsize=(10, 4.8))
        plt.bar(sub['model'], sub['mae'])
        plt.xticks(rotation=35, ha='right')
        plt.ylabel('MAE')
        plt.title(f'Test MAE by model - {dataset_key}')
        plt.tight_layout()
        plt.savefig(FIGURES / f'model_comparison_mae_{dataset_key}.png', dpi=160)
        plt.close()


def main():
    for dataset_key in DATASET_CONFIGS:
        plot_forecast_vs_actual(dataset_key)
        plot_error_over_time(dataset_key)
    plot_metric_comparison()
    print(f'Figures saved to {FIGURES}')


if __name__ == '__main__':
    main()
