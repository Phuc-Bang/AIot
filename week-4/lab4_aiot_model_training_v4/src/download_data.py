from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

from config import DATA_RAW, DATA_SAMPLE

APPLIANCES_URL = 'https://archive.ics.uci.edu/static/public/374/appliances+energy+prediction.zip'
OCCUPANCY_URL = 'https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip'


def try_download_zip(url: str, zip_path: Path, extract_to: Path) -> bool:
    try:
        print(f'Trying to download: {url}')
        
        with urllib.request.urlopen(url, timeout=12) as response:
            zip_path.write_bytes(response.read())
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_to)
        print(f'Downloaded and extracted to {extract_to}')
        return True
    except Exception as exc:
        print(f'Could not download {url}. Reason: {exc}')
        return False


def ensure_fallback_copy() -> None:
    # Copy classroom fallback files into raw/ so downstream scripts always have an input.
    fallback_pairs = [
        (DATA_SAMPLE / 'sample_energydata_complete.csv', DATA_RAW / 'energydata_complete.csv'),
        (DATA_SAMPLE / 'sample_occupancy_detection.csv', DATA_RAW / 'occupancy_combined.csv'),
    ]
    for src, dst in fallback_pairs:
        if not dst.exists():
            shutil.copyfile(src, dst)
            print(f'Using fallback sample: {dst}')


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    app_zip = DATA_RAW / 'appliances_energy_prediction.zip'
    occ_zip = DATA_RAW / 'occupancy_detection.zip'
    try_download_zip(APPLIANCES_URL, app_zip, DATA_RAW / 'appliances_official')
    try_download_zip(OCCUPANCY_URL, occ_zip, DATA_RAW / 'occupancy_official')
    ensure_fallback_copy()
    print('Data acquisition step completed. Official files are used when available; otherwise sample fallback files are used.')


if __name__ == '__main__':
    main()
