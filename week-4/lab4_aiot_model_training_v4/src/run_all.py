from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

cmds = [
    [sys.executable, 'src/download_data.py'],
    [sys.executable, 'src/prepare_datasets.py'],
    [sys.executable, 'src/train_classical_models.py'],
    [sys.executable, 'src/plot_results.py'],
    [sys.executable, 'src/compare_two_datasets.py'],
    [sys.executable, 'src/test_local_pipeline.py'],
]

for cmd in cmds:
    print('\n>>> ' + ' '.join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)
print('RUN_ALL_PASS')
