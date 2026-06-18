from __future__ import annotations

import csv
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

_lock = threading.Lock()


def append_csv_log(path: str | Path, row: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), **row}
    with _lock:
        exists = path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data.keys()))
            if not exists:
                writer.writeheader()
            writer.writerow(data)
