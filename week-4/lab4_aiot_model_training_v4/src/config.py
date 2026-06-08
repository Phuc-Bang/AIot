from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / 'data' / 'raw'
DATA_SAMPLE = ROOT / 'data' / 'sample'
DATA_PROCESSED = ROOT / 'data' / 'processed'
MODELS = ROOT / 'models'
OUTPUTS = ROOT / 'outputs'
FIGURES = ROOT / 'figures'

for _p in [DATA_RAW, DATA_SAMPLE, DATA_PROCESSED, MODELS, OUTPUTS, FIGURES]:
    _p.mkdir(parents=True, exist_ok=True)

DATASET_CONFIGS = {
    'appliances': {
        'display_name': 'UCI Appliances Energy Prediction',
        'processed_file': DATA_PROCESSED / 'appliances.csv',
        'sample_file': DATA_SAMPLE / 'sample_energydata_complete.csv',
        'target': 'Appliances',
        'timestamp': 'date',
        'horizon_steps': 3,       # 3 x 10 minutes = 30 minutes
        'horizon_minutes': 30,
        'lags': [1, 2, 3, 6, 12],
        'rolling_windows': [3, 6, 12],
        'sequence_length': 24,    # 4 hours of 10-minute readings
        'unit': 'Wh',
    },
    'co2': {
        'display_name': 'UCI Occupancy Detection / CO2 Forecasting',
        'processed_file': DATA_PROCESSED / 'co2.csv',
        'sample_file': DATA_SAMPLE / 'sample_occupancy_detection.csv',
        'target': 'CO2',
        'timestamp': 'date',
        'horizon_steps': 15,      # 15 x 1 minute = 15 minutes
        'horizon_minutes': 15,
        'lags': [1, 5, 10, 15, 30],
        'rolling_windows': [5, 15, 30],
        'sequence_length': 30,    # 30 minutes of one-minute readings
        'unit': 'ppm',
    },
}
