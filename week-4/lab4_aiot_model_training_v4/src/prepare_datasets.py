from __future__ import annotations

import shutil
from pathlib import Path
import pandas as pd

from config import DATA_RAW, DATA_SAMPLE, DATA_PROCESSED
from utils import print_header


def find_appliances_file() -> Path:
    candidates = list((DATA_RAW / 'appliances_official').rglob('energydata_complete.csv'))
    if candidates:
        return candidates[0]
    raw = DATA_RAW / 'energydata_complete.csv'
    if raw.exists():
        return raw
    return DATA_SAMPLE / 'sample_energydata_complete.csv'


def find_occupancy_files() -> list[Path]:
    official_dir = DATA_RAW / 'occupancy_official'
    candidates = []
    for name in ['datatraining.txt', 'datatest.txt', 'datatest2.txt']:
        hits = list(official_dir.rglob(name))
        candidates.extend(hits)
    if candidates:
        return candidates
    raw = DATA_RAW / 'occupancy_combined.csv'
    if raw.exists():
        return [raw]
    return [DATA_SAMPLE / 'sample_occupancy_detection.csv']


def prepare_appliances() -> Path:
    src = find_appliances_file()
    df = pd.read_csv(src)
    if 'date' not in df.columns or 'Appliances' not in df.columns:
        raise ValueError(f'Appliances file {src} must contain date and Appliances columns.')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    dst = DATA_PROCESSED / 'appliances.csv'
    df.to_csv(dst, index=False)
    print(f'Prepared appliances dataset: {dst} shape={df.shape} from {src}')
    return dst


def prepare_co2() -> Path:
    frames = []
    for src in find_occupancy_files():
        # Official files are comma-separated but may include an index column.
        df = pd.read_csv(src)
        unnamed = [c for c in df.columns if str(c).lower().startswith('unnamed')]
        if unnamed:
            df = df.drop(columns=unnamed)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    # Normalize capitalization sometimes seen in third-party copies.
    rename = {c: c.strip() for c in df.columns}
    df = df.rename(columns=rename)
    required = ['date', 'Temperature', 'Humidity', 'Light', 'CO2', 'HumidityRatio', 'Occupancy']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'Occupancy/CO2 dataset missing columns: {missing}')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    dst = DATA_PROCESSED / 'co2.csv'
    df.to_csv(dst, index=False)
    print(f'Prepared CO2 dataset: {dst} shape={df.shape}')
    return dst


def main() -> None:
    print_header('Preparing both datasets')
    prepare_appliances()
    prepare_co2()
    print('Prepared files are in data/processed/.')


if __name__ == '__main__':
    main()
