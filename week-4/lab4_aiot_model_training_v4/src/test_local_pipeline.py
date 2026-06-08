from __future__ import annotations

import pandas as pd

from config import OUTPUTS, MODELS, FIGURES

REQUIRED = [
    OUTPUTS / 'metrics_all_models.csv',
    OUTPUTS / 'model_comparison.csv',
    OUTPUTS / 'tuning_log.csv',
    OUTPUTS / 'predictions_appliances.csv',
    OUTPUTS / 'predictions_co2.csv',
    OUTPUTS / 'model_card_appliances.md',
    OUTPUTS / 'model_card_co2.md',
    MODELS / 'appliances_best_model.joblib',
    MODELS / 'co2_best_model.joblib',
    FIGURES / 'forecast_vs_actual_appliances.png',
    FIGURES / 'forecast_vs_actual_co2.png',
]


def main():
    missing = [str(p) for p in REQUIRED if not p.exists()]
    if missing:
        raise SystemExit('Missing required outputs:\n' + '\n'.join(missing))
    metrics = pd.read_csv(OUTPUTS / 'metrics_all_models.csv')
    expected_models = {
        'LastValue_baseline',
        'MovingAverage_baseline',
        'LinearRegression',
        'Ridge_alpha_1',
        'RandomForest_default',
        'GradientBoosting_advanced',
        'RandomForest_tuned',
    }
    for dataset in ['appliances', 'co2']:
        found = set(metrics.loc[(metrics['dataset'] == dataset) & (metrics['split'] == 'test'), 'model'])
        missing_models = expected_models - found
        if missing_models:
            raise SystemExit(f'{dataset} missing models: {missing_models}')
    print('LOCAL_PIPELINE_TEST_PASS')


if __name__ == '__main__':
    main()
