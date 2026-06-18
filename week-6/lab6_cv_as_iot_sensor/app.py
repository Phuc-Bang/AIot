"""
Lab 6 Enhanced — Computer Vision as IoT Sensor
===============================================
Nâng cấp toàn diện so với bản gốc:
  ✔ SQLite (thay CSV) — query linh hoạt, concurrent safe, có foreign key
  ✔ WebSocket — dashboard real-time, không polling 5s
  ✔ Multi-camera — đăng ký / quản lý nhiều camera, xem grid
  ✔ Background subtractor MOG2/KNN — motion detection thông minh hơn
  ✔ OpenCV HOG person detection — không dùng YOLO/ONNX/model ngoài
  ✔ MQTT publish (tùy chọn) — IoT integration thực tế
  ✔ Config YAML — không hardcode tham số
  ✔ Async camera I/O — không block event loop
  ✔ Docker hỗ trợ, sẵn sàng triển khai

Run:
    python app.py          # chạy với uvicorn
    uvicorn app:app --reload --host 0.0.0.0 --port 8000

Open:
    http://127.0.0.1:8000/
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import sqlite3
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
import cv2
import numpy as np
import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from PIL import Image

# ──────────────────────────────────────────────────────────────────────
# 1. CẤU HÌNH
# ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"

def load_config() -> dict:
    with open(str(CONFIG_PATH), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # merge defaults
    cfg.setdefault("server", {"host": "0.0.0.0", "port": 8000, "reload": True})
    cfg.setdefault("database", {"path": "outputs/lab6.db"})
    cfg.setdefault("camera", {"default_source": "0", "width": 640, "height": 480, "fps": 12, "fallback_to_simulated": True, "flip_mode": "none"})
    proc_defaults = {
        "resize_width": 320,
        "resize_height": 240,
        "threshold_value": 120,
        "canny_low": 80,
        "canny_high": 160,
        "brightness_threshold": 70,
        "filters": ["resize", "grayscale", "threshold", "edge"]
    }
    cfg.setdefault("processing", {})
    for k, v in proc_defaults.items():
        cfg["processing"].setdefault(k, v)
    motion_defaults = {
        "method": "mog2",
        "seconds": 3,
        "min_area": 800,
        "motion_score_threshold": 800,
        "simple_threshold": 25,
        "warmup_frames": 5,
        "min_contour_area": 120,
        "cooldown_seconds": 3,
        "mog2_history": 500,
        "mog2_var_threshold": 16,
        "detect_shadows": True,
    }
    cfg.setdefault("motion", {})
    for k, v in motion_defaults.items():
        cfg["motion"].setdefault(k, v)

    person_defaults = {
        "enabled": True,
        "detector_mode": "opencv_hog_person",
        "motion_overlap_threshold": 0.03,
        "min_motion_pixels_in_bbox": 150,
        "hog_hit_threshold": 0.0,
    }
    cfg.setdefault("person_detection", {})
    for k, v in person_defaults.items():
        cfg["person_detection"].setdefault(k, v)

    quality_defaults = {
        "brightness_min": 35,
        "brightness_max": 230,
        "blur_min_variance": 100.0,
    }
    cfg.setdefault("quality", {})
    for k, v in quality_defaults.items():
        cfg["quality"].setdefault(k, v)

    cfg.setdefault("debug", {"save_failed_frame": False})
    cfg.setdefault("mqtt", {"enabled": False, "broker": "localhost", "port": 1883, "client_id": "lab6_camera", "topic_prefix": "aiot/lab6", "qos": 1})
    cfg.setdefault("logging", {"level": "INFO", "file": "outputs/lab6.log"})

    # Environment variable overrides
    if os.getenv("MQTT_ENABLED"):
        cfg["mqtt"]["enabled"] = os.getenv("MQTT_ENABLED").lower() in ("true", "1", "yes")
    if os.getenv("MQTT_BROKER"):
        cfg["mqtt"]["broker"] = os.getenv("MQTT_BROKER")
    if os.getenv("MQTT_PORT"):
        try:
            cfg["mqtt"]["port"] = int(os.getenv("MQTT_PORT"))
        except ValueError:
            pass
    if os.getenv("CAMERA_SOURCE"):
        cfg["camera"]["default_source"] = os.getenv("CAMERA_SOURCE")

    return cfg

CFG = load_config()

# ── Paths ──
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw_images"
PROCESSED_DIR = DATA_DIR / "processed_images"
VIDEO_DIR = DATA_DIR / "videos"
OUTPUT_DIR = ROOT / "outputs"
MODELS_DIR = ROOT / "models"
STATIC_DIR = ROOT / "static"
DB_PATH = ROOT / CFG["database"]["path"]
DEBUG_DIR = DATA_DIR / "debug_frames"
PARAM_EXPERIMENT_LOG = OUTPUT_DIR / "parameter_experiment_log.csv"
INDEX_HTML = ROOT / "index.html"

NO_CACHE_HEADERS = {"Cache-Control": "no-store, max-age=0"}

for folder in [RAW_DIR, PROCESSED_DIR, VIDEO_DIR, OUTPUT_DIR, MODELS_DIR, STATIC_DIR, DEBUG_DIR, DB_PATH.parent, (ROOT / CFG["logging"]["file"]).parent]:
    folder.mkdir(parents=True, exist_ok=True)

# ── Logging ──
logging.basicConfig(
    level=getattr(logging, CFG["logging"]["level"].upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(ROOT / CFG["logging"]["file"]), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("lab6")

# ── Thread pool cho async camera I/O ──
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="camera_io")
last_person_motion_at: Dict[str, float] = {}

# ──────────────────────────────────────────────────────────────────────
# 2. DATABASE LAYER (SQLite)
# ──────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cameras (
    camera_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    label TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS images (
    image_id TEXT PRIMARY KEY,
    camera_id TEXT,
    device_id TEXT,
    timestamp TEXT,
    source_type TEXT,
    image_path TEXT,
    processed_path TEXT,
    width INTEGER,
    height INTEGER,
    brightness REAL,
    processing_status TEXT,
    processing_time_ms REAL,
    filters_applied TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    image_id TEXT,
    camera_id TEXT,
    timestamp TEXT,
    event_type TEXT,
    score REAL,
    severity TEXT,
    explanation TEXT,
    action_hint TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS detections (
    detection_id TEXT PRIMARY KEY,
    image_id TEXT,
    timestamp TEXT,
    label TEXT,
    confidence REAL,
    bbox_x INTEGER, bbox_y INTEGER, bbox_w INTEGER, bbox_h INTEGER
);

CREATE INDEX IF NOT EXISTS idx_images_ts ON images(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_detections_label ON detections(label);
CREATE INDEX IF NOT EXISTS idx_images_camera ON images(camera_id);
"""

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    # db.execute("PRAGMA foreign_keys=ON")  # FKs removed for simplicity
    return db

def init_db():
    db = get_db()
    db.executescript(SCHEMA_SQL)
    db.commit()
    db.close()

def db_insert(table: str, data: dict):
    db = get_db()
    try:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        db.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
        db.commit()
    finally:
        db.close()

def db_query(sql: str, params: tuple = (), limit: int = 20) -> List[dict]:
    db = get_db()
    try:
        db.row_factory = sqlite3.Row
        rows = db.execute(sql + " LIMIT ?", params + (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

def db_query_raw(sql: str, params: tuple = ()) -> List[dict]:
    db = get_db()
    try:
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

def db_query_one(sql: str, params: tuple = ()) -> Optional[dict]:
    rows = db_query(sql, params, limit=1)
    return rows[0] if rows else None

# ──────────────────────────────────────────────────────────────────────
# 3. CAMERA MANAGER (Multi-camera)
# ──────────────────────────────────────────────────────────────────────

class CameraStatus(Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class CameraInfo:
    camera_id: str
    source: str
    label: str = ""
    enabled: bool = True
    status: CameraStatus = CameraStatus.UNKNOWN
    last_seen: Optional[str] = None
    width: int = 640
    height: int = 480
    fps: int = 12

class CameraManager:
    def __init__(self):
        self._cameras: Dict[str, CameraInfo] = OrderedDict()
        self._captures: Dict[str, cv2.VideoCapture] = {}
        self._capture_locks: Dict[str, Lock] = {}
        self._capture_ref_counts: Dict[str, int] = {}
        self._stream_lock = Lock()
        self._stream_readers: Dict[str, str] = {}
        self._latest_frames: Dict[str, Tuple[np.ndarray, float, str]] = {}

    def _load_from_db(self):
        self._cameras.clear()
        rows = db_query("SELECT * FROM cameras WHERE enabled=1 ORDER BY created_at", limit=100)
        for r in rows:
            info = CameraInfo(
                camera_id=r["camera_id"],
                source=r["source"],
                label=r.get("label", ""),
                enabled=bool(r["enabled"]),
                status=CameraStatus.ONLINE if r.get("last_seen") else CameraStatus.UNKNOWN,
                last_seen=r.get("last_seen"),
            )
            self._cameras[info.camera_id] = info

    def register(self, source: str, label: str = "") -> CameraInfo:
        camera_id = f"cam_{uuid.uuid4().hex[:8]}"
        info = CameraInfo(camera_id=camera_id, source=source, label=label or source)
        self._cameras[camera_id] = info
        db_insert("cameras", {
            "camera_id": camera_id, "source": source,
            "label": label or source, "enabled": 1,
            "created_at": now_iso(), "last_seen": now_iso(),
        })
        log.info(f"Camera registered: {camera_id} -> {source}")
        return info

    def unregister(self, camera_id: str):
        self._cameras.pop(camera_id, None)
        self._release_capture(camera_id)
        db = get_db()
        try:
            db.execute("DELETE FROM cameras WHERE camera_id=?", (camera_id,))
            db.commit()
        finally:
            db.close()

    def update(self, camera_id: str, source: str, label: str = "") -> Optional[CameraInfo]:
        info = self._cameras.get(camera_id)
        if not info:
            return None
        if info.source != source:
            self._release_capture(camera_id)
            info.status = CameraStatus.UNKNOWN
        info.source = source
        info.label = label or source
        db = get_db()
        try:
            db.execute("UPDATE cameras SET source=?, label=? WHERE camera_id=?", (source, label or source, camera_id))
            db.commit()
        finally:
            db.close()
        log.info(f"Camera updated: {camera_id} -> {source} (label: {label})")
        return info

    def get_all(self) -> List[CameraInfo]:
        return list(self._cameras.values())

    def get(self, camera_id: str) -> Optional[CameraInfo]:
        return self._cameras.get(camera_id)

    def open_capture(self, camera_id: str, retain: bool = False) -> Tuple[Optional[cv2.VideoCapture], Optional[CameraInfo]]:
        info = self._cameras.get(camera_id)
        if not info:
            return None, None
        lock = self._capture_locks.setdefault(camera_id, Lock())
        with lock:
            cap = self._captures.get(camera_id)
            if cap is None or not cap.isOpened():
                src = self._parse_source(info.source)
                if isinstance(src, (int, str)) and str(src).isdigit():
                    cap = cv2.VideoCapture(int(src), cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(src)
                if info.width and info.height:
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, info.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, info.height)
                    except cv2.error:
                        pass
                if cap.isOpened():
                    self._captures[camera_id] = cap
                    info.status = CameraStatus.ONLINE
                    info.last_seen = now_iso()
                    self._update_last_seen(camera_id)
                else:
                    info.status = CameraStatus.OFFLINE
                    return None, info
            if retain:
                self._capture_ref_counts[camera_id] = self._capture_ref_counts.get(camera_id, 0) + 1
        return cap, info

    def release(self, camera_id: str):
        self._release_capture(camera_id, force=False)

    def _release_capture(self, camera_id: str, force: bool = True):
        lock = self._capture_locks.setdefault(camera_id, Lock())
        with lock:
            if not force:
                refs = self._capture_ref_counts.get(camera_id, 0)
                if refs > 1:
                    self._capture_ref_counts[camera_id] = refs - 1
                    return
                if refs == 1:
                    self._capture_ref_counts.pop(camera_id, None)
                elif refs <= 0:
                    return
            else:
                self._capture_ref_counts.pop(camera_id, None)
                with self._stream_lock:
                    self._stream_readers.pop(camera_id, None)
                    self._latest_frames.pop(camera_id, None)
            cap = self._captures.pop(camera_id, None)
            if cap:
                cap.release()

    def read_capture(self, camera_id: str, cap: cv2.VideoCapture) -> Tuple[bool, Optional[np.ndarray]]:
        lock = self._capture_locks.setdefault(camera_id, Lock())
        with lock:
            return cap.read()

    def acquire_stream_reader(self, camera_id: str, token: str) -> bool:
        with self._stream_lock:
            owner = self._stream_readers.get(camera_id)
            if owner is None or owner == token:
                self._stream_readers[camera_id] = token
                return True
            return False

    def release_stream_reader(self, camera_id: str, token: str):
        with self._stream_lock:
            if self._stream_readers.get(camera_id) == token:
                self._stream_readers.pop(camera_id, None)

    def set_latest_frame(self, camera_id: str, frame: np.ndarray, source_label: str):
        with self._stream_lock:
            self._latest_frames[camera_id] = (frame.copy(), time.time(), source_label)

    def get_latest_frame(self, camera_id: str, max_age_seconds: float = 2.0) -> Tuple[Optional[np.ndarray], Optional[str]]:
        with self._stream_lock:
            item = self._latest_frames.get(camera_id)
            if not item:
                return None, None
            frame, ts, source_label = item
            if time.time() - ts > max_age_seconds:
                return None, None
            return frame.copy(), source_label

    def release_all(self):
        for cid in list(self._captures.keys()):
            self._release_capture(cid, force=True)
        with self._stream_lock:
            self._stream_readers.clear()
            self._latest_frames.clear()

    def cleanup_stale(self, max_age_hours: int = 24):
        db = get_db()
        try:
            stale = db.execute(
                "SELECT camera_id FROM cameras WHERE last_seen IS NULL OR last_seen < datetime('now', ?)",
                (f"-{max_age_hours} hours",)
            ).fetchall()
            for row in stale:
                cid = row["camera_id"]
                self._cameras.pop(cid, None)
                self._release_capture(cid)
                db.execute("DELETE FROM cameras WHERE camera_id=?", (cid,))
                log.info(f"Cleaned stale camera: {cid}")
            db.commit()
        finally:
            db.close()

    def _update_last_seen(self, camera_id: str):
        db = get_db()
        try:
            db.execute("UPDATE cameras SET last_seen=? WHERE camera_id=?", (now_iso(), camera_id))
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _parse_source(source: str) -> Any:
        s = str(source).strip()
        return int(s) if s.isdigit() else s

camera_manager = CameraManager()

# ──────────────────────────────────────────────────────────────────────
# 4. WEBSOCKET CONNECTION MANAGER (Real-time)
# ──────────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active.discard(ws)

    async def broadcast(self, data: dict):
        async with self._lock:
            dead = set()
            for ws in self.active:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.add(ws)
            self.active -= dead

    @property
    def count(self) -> int:
        return len(self.active)

ws_manager = ConnectionManager()

# ──────────────────────────────────────────────────────────────────────
# 5. TIỆN ÍCH
# ──────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def relative_url(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
        return f"/files/{rel.as_posix()}"
    except Exception:
        return None

def validate_image_bytes(data: bytes) -> Image.Image:
    try:
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}") from exc

def pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def frame_to_jpeg_bytes(frame_bgr: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        raise RuntimeError("Could not encode frame as JPEG")
    return buffer.tobytes()

def compute_brightness(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))

def flip_frame_if_needed(frame: np.ndarray) -> np.ndarray:
    if frame is None:
        return frame
    mode = CFG["camera"].get("flip_mode", "none")
    if mode == "horizontal":
        return cv2.flip(frame, 1)
    elif mode == "vertical":
        return cv2.flip(frame, 0)
    elif mode == "both":
        return cv2.flip(frame, -1)
    return frame

# ──────────────────────────────────────────────────────────────────────
# 6. IMAGE PROCESSING PIPELINE (ENHANCED)
# ──────────────────────────────────────────────────────────────────────

def apply_filter_resize(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    w, h = config.get("resize_width", 320), config.get("resize_height", 240)
    r = cv2.resize(frame_bgr, (w, h))
    return "RESIZE", r

def apply_filter_grayscale(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    return "GRAYSCALE", cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def apply_filter_threshold(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    val = config.get("threshold_value", 120)
    _, th = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY)
    return f"THRESHOLD({val})", cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)

def apply_filter_edge(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    low = config.get("canny_low", 80)
    high = config.get("canny_high", 160)
    edges = cv2.Canny(gray, low, high)
    return f"EDGE({low},{high})", cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

def apply_filter_gaussian_blur(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    b = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
    return "GAUSSIAN_BLUR", b

def apply_filter_histogram_equalize(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    eq = cv2.equalizeHist(gray)
    return "HIST_EQ", cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR)

def apply_filter_sobel_x(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sx = np.uint8(np.clip(np.abs(sx), 0, 255))
    return "SOBEL_X", cv2.cvtColor(sx, cv2.COLOR_GRAY2BGR)

def apply_filter_sobel_y(gray: np.ndarray, frame_bgr: np.ndarray, config: dict) -> Tuple[str, np.ndarray]:
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sy = np.uint8(np.clip(np.abs(sy), 0, 255))
    return "SOBEL_Y", cv2.cvtColor(sy, cv2.COLOR_GRAY2BGR)

FILTER_REGISTRY = {
    "resize": apply_filter_resize,
    "grayscale": apply_filter_grayscale,
    "threshold": apply_filter_threshold,
    "edge": apply_filter_edge,
    "gaussian_blur": apply_filter_gaussian_blur,
    "histogram_equalize": apply_filter_histogram_equalize,
    "sobel_x": apply_filter_sobel_x,
    "sobel_y": apply_filter_sobel_y,
}

def create_processed_contact_sheet(
    frame_bgr: np.ndarray,
    image_id: str,
    filters: Optional[List[str]] = None,
    config: Optional[dict] = None,
) -> Tuple[Path, float, Dict[str, Any]]:
    if filters is None:
        filters = ["resize", "grayscale", "threshold", "edge"]
    if config is None:
        config = CFG["processing"]

    start = time.perf_counter()
    base = cv2.resize(frame_bgr, (config.get("resize_width", 320), config.get("resize_height", 240)))
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

    tiles: List[Tuple[str, np.ndarray]] = []
    for fname in filters:
        func = FILTER_REGISTRY.get(fname)
        if func:
            try:
                label, tile = func(gray, base, config)
                tiles.append((label, tile))
            except Exception as e:
                log.warning(f"Filter '{fname}' failed: {e}")

    if not tiles:
        resized = cv2.resize(frame_bgr, (config.get("resize_width", 320), config.get("resize_height", 240)))
        tiles.append(("RESIZE", resized))

    tile_w = config.get("resize_width", 320)
    tile_h = config.get("resize_height", 240)

    def add_label(img: np.ndarray, text: str) -> np.ndarray:
        canvas = img.copy()
        cv2.rectangle(canvas, (0, 0), (tile_w, 30), (255, 255, 255), -1)
        cv2.putText(canvas, text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        return canvas

    # Arrange tiles in a 2-column grid
    rows_list = []
    for i in range(0, len(tiles), 2):
        row_tiles = []
        for j in range(2):
            if i + j < len(tiles):
                label_text, tile_img = tiles[i + j]
                row_tiles.append(add_label(tile_img, f"{i+j+1}. {label_text}"))
            else:
                blank = np.full((tile_h, tile_w, 3), 245, dtype=np.uint8)
                row_tiles.append(add_label(blank, ""))
        rows_list.append(np.hstack(row_tiles))

    sheet = np.vstack(rows_list) if rows_list else np.full((tile_h, tile_w, 3), 245, dtype=np.uint8)

    out_path = PROCESSED_DIR / f"{image_id}_processed_steps.jpg"
    cv2.imwrite(str(out_path), sheet)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    stats = {
        "brightness": round(compute_brightness(frame_bgr), 2),
        "width": int(frame_bgr.shape[1]),
        "height": int(frame_bgr.shape[0]),
    }
    return out_path, elapsed_ms, stats

# ──────────────────────────────────────────────────────────────────────
# 7. OBJECT DETECTION (OpenCV HOG Person Detector)
# ──────────────────────────────────────────────────────────────────────

class HogPersonDetector:
    def __init__(self, config: dict):
        self.cfg = config
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        log.info("OpenCV HOG Person Detector initialized")

    @property
    def available(self) -> bool:
        return True

    def detect(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        if not self.cfg.get("enabled", True):
            return []
        
        hit_threshold = self.cfg.get("hog_hit_threshold", 0.0)
        
        # Run HOG detector
        rects, weights = self.hog.detectMultiScale(
            frame_bgr,
            hitThreshold=hit_threshold,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05
        )
        
        # Apply NMS using cv2.dnn.NMSBoxes
        boxes = []
        for (x, y, w, h) in rects:
            boxes.append([int(x), int(y), int(w), int(h)])
        
        indices = []
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                [float(w) for w in weights],
                score_threshold=0.0,
                nms_threshold=0.3
            )
            indices = np.array(indices).flatten() if len(indices) > 0 else []
            
        results = []
        for i in indices:
            x, y, w, h = boxes[i]
            results.append({
                "label": "person",
                "confidence": round(float(weights[i]), 3),
                "bbox": {"x": x, "y": y, "w": w, "h": h}
            })
        return results

    def draw_detections(self, frame_bgr: np.ndarray, detections: List[dict]) -> np.ndarray:
        canvas = frame_bgr.copy()
        for det in detections:
            b = det["bbox"]
            x1, y1, x2, y2 = b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label_text = f"{det['label']} {det['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(canvas, (x1, y1-th-8), (x1+tw+8, y1), (0, 255, 0), -1)
            cv2.putText(canvas, label_text, (x1+4, y1-4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 34), (255, 255, 255), -1)
        cv2.putText(canvas, "OBJECT DETECTION | opencv_hog_person", (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 2)
        return canvas

detector = HogPersonDetector(CFG["person_detection"])

def compute_blur_score(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def evaluate_frame_quality(frame_bgr: np.ndarray) -> Dict[str, Any]:
    brightness = round(compute_brightness(frame_bgr), 2)
    blur_score = round(compute_blur_score(frame_bgr), 2)
    warnings: List[str] = []
    if brightness < CFG["quality"].get("brightness_min", 35):
        warnings.append("LOW_QUALITY_DARK")
    if brightness > CFG["quality"].get("brightness_max", 230):
        warnings.append("LOW_QUALITY_OVEREXPOSED")
    if blur_score < CFG["quality"].get("blur_min_variance", 100.0):
        warnings.append("LOW_QUALITY_BLURRY")
    return {"brightness": brightness, "blur_score": blur_score, "warnings": warnings}

def clean_motion_mask(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask

def motion_score_from_mask(mask: np.ndarray, min_contour_area: int) -> Tuple[float, List[np.ndarray]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid = [c for c in contours if cv2.contourArea(c) >= min_contour_area]
    return float(sum(cv2.contourArea(c) for c in valid)), valid

def annotate_person_motion(
    detections: List[Dict[str, Any]],
    motion_mask: np.ndarray,
    frame_shape: Tuple[int, int, int],
    overlap_threshold: float,
    min_motion_pixels: int,
) -> List[Dict[str, Any]]:
    frame_h, frame_w = frame_shape[:2]
    annotated: List[Dict[str, Any]] = []
    for det in detections:
        bbox = det.get("bbox", {})
        x = max(0, int(bbox.get("x", 0)))
        y = max(0, int(bbox.get("y", 0)))
        w = max(0, int(bbox.get("w", 0)))
        h = max(0, int(bbox.get("h", 0)))
        x2 = min(frame_w, x + w)
        y2 = min(frame_h, y + h)
        w = max(0, x2 - x)
        h = max(0, y2 - y)
        if w == 0 or h == 0:
            motion_pixels = 0
            overlap_ratio = 0.0
        else:
            roi = motion_mask[y:y2, x:x2]
            motion_pixels = int(cv2.countNonZero(roi)) if roi.size else 0
            overlap_ratio = motion_pixels / float(w * h)
        item = dict(det)
        item["bbox"] = {"x": x, "y": y, "w": w, "h": h}
        item["motion_pixels_in_bbox"] = motion_pixels
        item["motion_overlap_ratio"] = round(overlap_ratio, 4)
        item["is_moving_person"] = motion_pixels >= min_motion_pixels and overlap_ratio >= overlap_threshold
        annotated.append(item)
    return annotated

def append_parameter_experiment(row: Dict[str, Any]) -> None:
    fieldnames = [
        "timestamp", "camera_id", "method", "seconds", "frames_seen", "motion_score",
        "threshold", "min_contour_area", "warmup_frames", "person_count",
        "moving_person_count", "best_overlap_ratio", "brightness", "blur_score",
        "reason_code", "person_motion_detected",
    ]
    PARAM_EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    exists = PARAM_EXPERIMENT_LOG.exists()
    with PARAM_EXPERIMENT_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})

def save_motion_debug_artifacts(
    camera_id: str,
    frame: Optional[np.ndarray],
    motion_mask: Optional[np.ndarray],
    detections: List[Dict[str, Any]],
    payload: Dict[str, Any],
) -> Dict[str, str]:
    debug_id = f"dbg_{uuid.uuid4().hex[:10]}"
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    if frame is not None:
        frame_path = DEBUG_DIR / f"{debug_id}_frame.jpg"
        cv2.imwrite(str(frame_path), frame)
        paths["frame_url"] = relative_url(frame_path)
        if motion_mask is not None:
            mask_path = DEBUG_DIR / f"{debug_id}_mask.jpg"
            cv2.imwrite(str(mask_path), motion_mask)
            paths["mask_url"] = relative_url(mask_path)
            annotated = draw_debug_annotations(
                frame,
                detections,
                motion_mask,
                CFG["person_detection"].get("motion_overlap_threshold", 0.03),
                CFG["person_detection"].get("min_motion_pixels_in_bbox", 150),
            )
            annotated_path = DEBUG_DIR / f"{debug_id}_annotated.jpg"
            cv2.imwrite(str(annotated_path), annotated)
            paths["annotated_url"] = relative_url(annotated_path)
    json_path = DEBUG_DIR / f"{debug_id}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"camera_id": camera_id, **payload, "files": paths}, f, ensure_ascii=False, indent=2)
    paths["json_url"] = relative_url(json_path)
    return paths

def draw_debug_annotations(frame: np.ndarray, detections: list, mask: np.ndarray, overlap_thresh: float, min_pixels: int) -> np.ndarray:
    canvas = frame.copy()
    frame_h, frame_w = frame.shape[:2]
    
    # Draw motion mask as semi-transparent red overlay
    mask_colored = np.zeros_like(frame)
    mask_colored[:, :, 2] = mask  # Kênh màu đỏ
    canvas = cv2.addWeighted(canvas, 0.8, mask_colored, 0.3, 0)
    
    for det in detections:
        bbox = det["bbox"]
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        x_min, y_min = max(0, x), max(0, y)
        x_max, y_max = min(frame_w, x+w), min(frame_h, y+h)
        sub_mask = mask[y_min:y_max, x_min:x_max]
        pixels = int(cv2.countNonZero(sub_mask)) if sub_mask.size > 0 else 0
        ratio = pixels / (w * h) if (w * h) > 0 else 0.0
        
        is_moving = pixels >= min_pixels and ratio >= overlap_thresh
        color = (0, 255, 0) if is_moving else (0, 0, 255) # Màu xanh nếu chuyển động, đỏ nếu không
        cv2.rectangle(canvas, (x, y), (x+w, y+h), color, 2)
        
        text = f"person: {ratio:.2f} ({pixels}px)"
        cv2.rectangle(canvas, (x, y-18), (x+150, y), color, -1)
        cv2.putText(canvas, text, (x+4, y-4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
    return canvas

# ──────────────────────────────────────────────────────────────────────
# 8. MQTT CLIENT (Tùy chọn)
# ──────────────────────────────────────────────────────────────────────

class MqttClient:
    def __init__(self, config: dict):
        self.cfg = config
        self.client = None

    def connect(self):
        if not self.cfg.get("enabled", False):
            return
        try:
            import paho.mqtt.client as mqtt
            self.client = mqtt.Client(client_id=self.cfg.get("client_id", "lab6_camera"))
            self.client.connect(self.cfg.get("broker", "localhost"), self.cfg.get("port", 1883))
            self.client.loop_start()
            log.info(f"MQTT connected to {self.cfg['broker']}:{self.cfg['port']}")
        except Exception as e:
            log.warning(f"MQTT connection failed: {e}. MQTT disabled.")
            self.client = None

    def publish(self, topic_suffix: str, data: dict):
        if self.client is None:
            return
        try:
            topic = f"{self.cfg.get('topic_prefix', 'aiot/lab6')}/{topic_suffix}"
            self.client.publish(topic, json.dumps(data, ensure_ascii=False), qos=self.cfg.get("qos", 1))
        except Exception as e:
            log.warning(f"MQTT publish failed: {e}")

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

mqtt_client = MqttClient(CFG["mqtt"])

# ──────────────────────────────────────────────────────────────────────
# 9. SIMULATED FRAME (Fallback)
# ──────────────────────────────────────────────────────────────────────

def simulated_frame(counter: int = 0, width: int = 640, height: int = 360) -> np.ndarray:
    frame = np.full((height, width, 3), 245, dtype=np.uint8)
    x = 30 + (counter * 12) % max(1, width - 180)
    y = 80 + (counter * 7) % max(1, height - 170)
    cv2.rectangle(frame, (x, 120), (x + 130, 240), (40, 140, 240), -1)
    cv2.circle(frame, (width - 110, y), 38, (80, 200, 120), -1)
    cv2.putText(frame, "SIMULATED CAMERA STREAM", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(frame, "Use source=0 for laptop camera or URL for IP camera", (25, height - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return frame

# ──────────────────────────────────────────────────────────────────────
# 10. MAIN PIPELINE
# ──────────────────────────────────────────────────────────────────────

async def log_image_pipeline(
    frame_bgr: np.ndarray,
    source_type: str,
    device_id: str,
    camera_id: Optional[str] = None,
    note: str = "",
    filters: Optional[List[str]] = None,
    run_detection: bool = False,
) -> Dict[str, Any]:
    image_id = f"img_{uuid.uuid4().hex[:10]}"
    timestamp = now_iso()

    # Save raw image (async to thread)
    raw_path = RAW_DIR / f"{image_id}.jpg"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, lambda: cv2.imwrite(str(raw_path), frame_bgr))

    # Process image
    if filters is None:
        filters = CFG["processing"].get("filters", ["resize", "grayscale", "threshold", "edge"])
    processed_path, processing_time_ms, stats = await loop.run_in_executor(
        executor, create_processed_contact_sheet, frame_bgr, image_id, filters, CFG["processing"]
    )
    brightness = stats["brightness"]

    # Insert metadata
    meta = {
        "image_id": image_id,
        "camera_id": camera_id,
        "device_id": device_id,
        "timestamp": timestamp,
        "source_type": source_type,
        "image_path": str(raw_path.relative_to(ROOT)),
        "processed_path": str(processed_path.relative_to(ROOT)),
        "width": stats["width"],
        "height": stats["height"],
        "brightness": brightness,
        "processing_status": "processed",
        "processing_time_ms": processing_time_ms,
        "filters_applied": json.dumps(filters),
        "note": note,
    }
    db_insert("images", meta)

    # Quality check
    blur_score = compute_blur_score(frame_bgr)
    warnings = []
    if brightness < CFG["processing"].get("brightness_threshold", 70):
        warnings.append("LOW_LIGHT")
    if blur_score < CFG["quality"].get("blur_min_variance", 100.0):
        warnings.append("BLURRY")
    quality = {
        "brightness": round(brightness, 2),
        "blur_score": round(blur_score, 2),
        "warnings": warnings
    }

    # Generate event
    if warnings:
        event_type = "IMAGE_QUALITY_WARNING"
        severity = "WARNING"
        explanation = f"Quality checks failed: {', '.join(warnings)}"
        action_hint = "Improve lighting or stability."
    else:
        event_type = "IMAGE_PROCESSED"
        severity = "NORMAL"
        explanation = "Image was received, saved, preprocessed, and registered."
        action_hint = "Continue monitoring."

    event_row = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "image_id": image_id,
        "camera_id": camera_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "score": brightness,
        "severity": severity,
        "explanation": explanation,
        "action_hint": action_hint,
        "metadata": json.dumps({"source_type": source_type, "note": note, "quality": quality}),
    }
    db_insert("events", event_row)

    # Object detection
    detections = []
    detector_mode = "none"
    if run_detection:
        try:
            detector_mode = "opencv_hog_person"
            detections = await loop.run_in_executor(executor, detector.detect, frame_bgr)
            for det in detections:
                db_insert("detections", {
                    "detection_id": f"det_{uuid.uuid4().hex[:10]}",
                    "image_id": image_id,
                    "timestamp": timestamp,
                    "label": det["label"],
                    "confidence": det["confidence"],
                    "bbox_x": det["bbox"]["x"],
                    "bbox_y": det["bbox"]["y"],
                    "bbox_w": det["bbox"]["w"],
                    "bbox_h": det["bbox"]["h"],
                })
            if detections:
                det_event = {
                    "event_id": f"evt_{uuid.uuid4().hex[:10]}",
                    "image_id": image_id,
                    "camera_id": camera_id,
                    "timestamp": timestamp,
                    "event_type": "DETECTED_PERSON",
                    "score": detections[0]["confidence"],
                    "severity": "NORMAL",
                    "explanation": f"Detected {len(detections)} person(s) using OpenCV HOG.",
                    "action_hint": "Review detection results in dashboard.",
                    "metadata": json.dumps({"detections": detections, "detector_mode": detector_mode, "quality": quality}),
                }
                db_insert("events", det_event)
                event_row = det_event
        except Exception as e:
            log.error(f"Detection error: {e}")

    # MQTT publish
    mqtt_client.publish("events", event_row)
    mqtt_client.publish("metadata", meta)
    if detections:
        mqtt_client.publish("detections", {"image_id": image_id, "detections": detections})

    # WebSocket broadcast
    await ws_manager.broadcast({
        "type": "new_image",
        "image_id": image_id,
        "event": event_row,
        "detections": detections,
        "raw_image_url": relative_url(raw_path),
        "processed_image_url": relative_url(processed_path),
        "quality": quality,
    })

    return {
        "image_id": image_id,
        "metadata": meta,
        "event": event_row,
        "detections": detections,
        "raw_image_url": relative_url(raw_path),
        "processed_image_url": relative_url(processed_path),
        "quality": quality,
    }

# ──────────────────────────────────────────────────────────────────────
# 11. VIDEO STREAMING (Async)
# ──────────────────────────────────────────────────────────────────────

async def stream_frames(camera_id: str) -> AsyncIterator[bytes]:
    info = camera_manager.get(camera_id)
    counter = 0
    use_simulated = False
    cap = None
    reader_token = uuid.uuid4().hex
    owns_reader = False
    loop = asyncio.get_event_loop()
    try:
        while True:
            frame = None
            source_label = "SIMULATED"

            if not owns_reader:
                owns_reader = camera_manager.acquire_stream_reader(camera_id, reader_token)

            if owns_reader and not use_simulated:
                if cap is None:
                    cap, info = await loop.run_in_executor(executor, camera_manager.open_capture, camera_id, True)
                if cap is not None:
                    ok, frame = await loop.run_in_executor(executor, camera_manager.read_capture, camera_id, cap)
                    if ok and frame is not None:
                        frame = flip_frame_if_needed(frame)
                        source_label = "LIVE"
                        camera_manager.set_latest_frame(camera_id, frame, source_label)
                    else:
                        if cap is not None:
                            cap = None
                            camera_manager.release(camera_id)
                        use_simulated = True
                else:
                    use_simulated = True
            elif not owns_reader:
                frame, source_label = camera_manager.get_latest_frame(camera_id, max_age_seconds=3.0)
                if frame is not None:
                    source_label = source_label or "LIVE-CACHED"

            if use_simulated and counter > 0 and counter % 60 == 0:
                if cap is not None:
                    cap = None
                    camera_manager.release(camera_id)
                use_simulated = False
                continue

            if use_simulated or frame is None:
                w = info.width if info else 640
                h = info.height if info else 360
                frame = simulated_frame(counter, w, h)
                source_label = "SIMULATED"
                if owns_reader:
                    camera_manager.set_latest_frame(camera_id, frame, source_label)

            cam_label = info.label if info else camera_id
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 32), (255, 255, 255), -1)
            cv2.putText(frame, f"{source_label} | {cam_label} | frame={counter}",
                        (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

            jpg = frame_to_jpeg_bytes(frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            counter += 1
            await asyncio.sleep(1.0 / CFG["camera"].get("fps", 12))
    finally:
        if cap is not None:
            camera_manager.release(camera_id)
        if owns_reader:
            camera_manager.release_stream_reader(camera_id, reader_token)

# ──────────────────────────────────────────────────────────────────────
# 12. VIDEO RECORDING
# ──────────────────────────────────────────────────────────────────────

def record_short_video(camera_id: str, seconds: int = 5, width: int = 640, height: int = 360) -> Dict[str, Any]:
    seconds = max(1, min(int(seconds), 30))
    info = camera_manager.get(camera_id)

    fps = 10
    video_id = f"vid_{uuid.uuid4().hex[:10]}"
    out_path = VIDEO_DIR / f"{video_id}.mp4"
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_count = 0
    start = time.perf_counter()

    backup_cap = None
    if info:
        cap, _ = camera_manager.open_capture(camera_id)
        if cap is None:
            backup_cap = cv2.VideoCapture(camera_manager._parse_source(info.source))
            cap = backup_cap if backup_cap.isOpened() else None

    try:
        while time.perf_counter() - start < seconds:
            if cap is not None:
                ok, frame = cap.read()
                if ok and frame is not None:
                    frame = flip_frame_if_needed(frame)
                else:
                    frame = simulated_frame(frame_count, width, height)
            else:
                frame = simulated_frame(frame_count, width, height)
            frame = cv2.resize(frame, (width, height))
            writer.write(frame)
            frame_count += 1
            time.sleep(1.0 / fps)
    finally:
        if backup_cap is not None:
            backup_cap.release()
        writer.release()

    event_row = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "image_id": video_id,
        "camera_id": camera_id,
        "timestamp": now_iso(),
        "event_type": "VIDEO_RECORDED",
        "score": frame_count,
        "severity": "NORMAL",
        "explanation": f"Recorded a short video clip with {frame_count} frames.",
        "action_hint": "Use the video clip for later review or image analysis.",
        "metadata": json.dumps({"seconds": seconds, "fps": fps}),
    }
    db_insert("events", event_row)
    mqtt_client.publish("events", event_row)
    return {
        "video_id": video_id,
        "video_path": str(out_path.relative_to(ROOT)),
        "video_url": relative_url(out_path),
        "seconds": seconds,
        "frames": frame_count,
        "event": event_row,
    }

# ──────────────────────────────────────────────────────────────────────
# 13. MOTION CAPTURE (ADVANCED — MOG2)
# ──────────────────────────────────────────────────────────────────────

async def motion_capture(
    camera_id: str,
    seconds: int = 3,
    method: str = "mog2",
    min_area: Optional[int] = None,
    simple_threshold: int = 25,
    debug: bool = False,
) -> Dict[str, Any]:
    seconds = max(1, min(int(seconds), 30))
    method = (method or CFG["motion"].get("method", "mog2")).lower()
    if method not in {"mog2", "knn", "simple"}:
        method = CFG["motion"].get("method", "mog2")
    threshold = float(min_area if min_area is not None else CFG["motion"].get("motion_score_threshold", CFG["motion"].get("min_area", 800)))
    warmup_frames = int(CFG["motion"].get("warmup_frames", 5))
    min_contour_area = int(CFG["motion"].get("min_contour_area", 120))
    cooldown_seconds = float(CFG["motion"].get("cooldown_seconds", 3))
    overlap_threshold = float(CFG["person_detection"].get("motion_overlap_threshold", 0.03))
    min_motion_pixels = int(CFG["person_detection"].get("min_motion_pixels_in_bbox", 150))

    info = camera_manager.get(camera_id)

    subtractor = None
    if method == "mog2":
        subtractor = cv2.createBackgroundSubtractorMOG2(
            history=CFG["motion"].get("mog2_history", 500),
            varThreshold=CFG["motion"].get("mog2_var_threshold", 16),
            detectShadows=CFG["motion"].get("detect_shadows", True),
        )
    elif method == "knn":
        subtractor = cv2.createBackgroundSubtractorKNN(
            history=CFG["motion"].get("mog2_history", 500),
            dist2Threshold=CFG["motion"].get("mog2_var_threshold", 16) * 16,
            detectShadows=CFG["motion"].get("detect_shadows", True),
        )

    prev_gray = None
    best_frame = None
    best_motion_mask = None
    best_score = -1.0
    frames_seen = 0
    scored_frames = 0
    start = time.perf_counter()

    loop = asyncio.get_event_loop()

    cap = None
    if info:
        src = camera_manager._parse_source(info.source)
        def _open():
            use_dshow = isinstance(src, (int, str)) and str(src).isdigit()
            cap = cv2.VideoCapture(int(src), cv2.CAP_DSHOW) if use_dshow else cv2.VideoCapture(src)
            return cap
        cap = await loop.run_in_executor(executor, _open)
    if (cap is None or not cap.isOpened()) and not CFG["camera"].get("fallback_to_simulated", True):
        if cap is not None:
            cap.release()
            cap = None
        reason_code = "CAMERA_OPEN_FAILED"
        reason = "Could not open camera source."
        quality = {"brightness": None, "blur_score": None, "warnings": []}
        response = {
            "person_motion_detected": False,
            "reason_code": reason_code,
            "reason": reason,
            "motion_score": 0.0,
            "person_detections": [],
            "person_count": 0,
            "best_overlap_ratio": 0.0,
            "quality": quality,
            "frames_seen": 0,
            "method": method,
            "debug": debug,
        }
        db_insert("events", {
            "event_id": f"evt_{uuid.uuid4().hex[:10]}",
            "image_id": None,
            "camera_id": camera_id,
            "timestamp": now_iso(),
            "event_type": "NO_PERSON_MOTION",
            "score": 0.0,
            "severity": "ERROR",
            "explanation": reason,
            "action_hint": "Check camera connection and source URL.",
            "metadata": json.dumps(response),
        })
        append_parameter_experiment({
            "timestamp": now_iso(), "camera_id": camera_id, "method": method,
            "frames_seen": 0, "motion_score": 0.0, "threshold": threshold,
            "min_contour_area": min_contour_area, "warmup_frames": warmup_frames,
            "person_count": 0, "moving_person_count": 0, "best_overlap_ratio": 0.0,
            "reason_code": reason_code, "person_motion_detected": False,
        })
        await ws_manager.broadcast({"type": "motion_result", **response})
        return response
    if cap is not None and not cap.isOpened():
        cap.release()
        cap = None

    def _frame_subtractor(f):
        fg = subtractor.apply(f)
        mask = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]
        mask = clean_motion_mask(mask)
        score, _ = motion_score_from_mask(mask, min_contour_area)
        return score, mask

    def _frame_simple(f, pg):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(g, (5, 5), 0)
        if pg is not None:
            d = cv2.absdiff(pg, g)
            _, mask = cv2.threshold(d, simple_threshold, 255, cv2.THRESH_BINARY)
            mask = clean_motion_mask(mask)
            score, _ = motion_score_from_mask(mask, min_contour_area)
            return score, mask, g
        return 0.0, np.zeros(g.shape, dtype=np.uint8), g

    try:
        while time.perf_counter() - start < seconds:
            if cap is not None:
                ok, frame = await loop.run_in_executor(executor, cap.read)
                if ok and frame is not None:
                    frame = flip_frame_if_needed(frame)
                else:
                    frame = simulated_frame(frames_seen)
            else:
                frame = simulated_frame(frames_seen)
            frames_seen += 1

            if subtractor is not None:
                score, motion_mask = await loop.run_in_executor(executor, _frame_subtractor, frame)
            else:
                score, motion_mask, prev_gray = await loop.run_in_executor(executor, _frame_simple, frame, prev_gray)

            if frames_seen <= warmup_frames:
                await asyncio.sleep(0.05)
                continue

            scored_frames += 1
            if score >= best_score:
                best_score = score
                best_frame = frame.copy()
                best_motion_mask = motion_mask.copy()

            await asyncio.sleep(0.05)
    finally:
        if cap is not None:
            cap.release()

    if best_frame is None:
        reason_code = "NO_FRAMES_CAPTURED" if frames_seen == 0 or scored_frames == 0 else "NO_GLOBAL_MOTION"
        quality = {"brightness": None, "blur_score": None, "warnings": []}
        response = {
            "person_motion_detected": False,
            "reason_code": reason_code,
            "reason": "No scorable frames were captured." if reason_code == "NO_FRAMES_CAPTURED" else "No global motion exceeded the configured threshold.",
            "motion_score": round(best_score, 2),
            "person_detections": [],
            "person_count": 0,
            "best_overlap_ratio": 0.0,
            "quality": quality,
            "frames_seen": frames_seen,
            "method": method,
        }
        db_insert("events", {
            "event_id": f"evt_{uuid.uuid4().hex[:10]}",
            "image_id": None,
            "camera_id": camera_id,
            "timestamp": now_iso(),
            "event_type": "NO_PERSON_MOTION",
            "score": round(best_score, 2),
            "severity": "NORMAL",
            "explanation": response["reason"],
            "action_hint": "Continue monitoring or enable debug=true for diagnostics.",
            "metadata": json.dumps(response),
        })
        append_parameter_experiment({
            "timestamp": now_iso(), "camera_id": camera_id, "method": method, "seconds": seconds,
            "frames_seen": frames_seen, "motion_score": round(best_score, 2), "threshold": threshold,
            "min_contour_area": min_contour_area, "warmup_frames": warmup_frames,
            "person_count": 0, "moving_person_count": 0, "best_overlap_ratio": 0.0,
            "reason_code": reason_code, "person_motion_detected": False,
        })
        await ws_manager.broadcast({"type": "motion_result", **response})
        return response

    if best_motion_mask is None:
        best_motion_mask = np.zeros(best_frame.shape[:2], dtype=np.uint8)

    quality = evaluate_frame_quality(best_frame)
    raw_detections = await loop.run_in_executor(executor, detector.detect, best_frame)
    person_detections = annotate_person_motion(raw_detections, best_motion_mask, best_frame.shape, overlap_threshold, min_motion_pixels)
    moving_people = [d for d in person_detections if d.get("is_moving_person")]
    best_overlap_ratio = max([d.get("motion_overlap_ratio", 0.0) for d in person_detections] or [0.0])

    now_perf = time.perf_counter()
    cooldown_until = last_person_motion_at.get(camera_id, 0.0) + cooldown_seconds
    if now_perf < cooldown_until:
        reason_code = "COOLDOWN_ACTIVE"
        reason = f"Person motion was recently confirmed; cooldown active for {cooldown_until - now_perf:.1f}s."
    elif best_score < threshold:
        reason_code = "NO_GLOBAL_MOTION"
        reason = f"Motion score {best_score:.0f} is below threshold {threshold:.0f}."
    elif "LOW_QUALITY_DARK" in quality["warnings"]:
        reason_code = "LOW_QUALITY_DARK"
        reason = "Frame is too dark for reliable person-motion detection."
    elif "LOW_QUALITY_OVEREXPOSED" in quality["warnings"]:
        reason_code = "LOW_QUALITY_OVEREXPOSED"
        reason = "Frame is overexposed for reliable person-motion detection."
    elif "LOW_QUALITY_BLURRY" in quality["warnings"]:
        reason_code = "LOW_QUALITY_BLURRY"
        reason = "Frame is too blurry for reliable person-motion detection."
    elif not person_detections:
        reason_code = "NO_PERSON_DETECTED"
        reason = "OpenCV HOG did not detect a person in the best motion frame."
    elif not moving_people:
        reason_code = "PERSON_NO_MOTION_OVERLAP"
        reason = "Person bbox exists, but motion pixels inside the bbox are below thresholds."
    else:
        reason_code = "PERSON_MOTION_CONFIRMED"
        reason = "A person bbox contains enough motion pixels."

    person_motion_detected = reason_code == "PERSON_MOTION_CONFIRMED"
    base_response = {
        "person_motion_detected": person_motion_detected,
        "reason_code": reason_code,
        "reason": reason,
        "motion_score": round(best_score, 2),
        "motion_threshold": threshold,
        "person_detections": person_detections,
        "person_count": len(person_detections),
        "moving_person_count": len(moving_people),
        "best_overlap_ratio": round(best_overlap_ratio, 4),
        "quality": quality,
        "frames_seen": frames_seen,
        "scored_frames": scored_frames,
        "method": method,
        "debug": debug,
    }

    if person_motion_detected:
        result = await log_image_pipeline(
            best_frame,
            source_type="person_motion_capture",
            device_id=f"camera:{camera_id}",
            camera_id=camera_id,
            note=f"person_motion_score={round(best_score, 2)}, method={method}",
            run_detection=False,
        )
        timestamp = now_iso()
        for det in moving_people:
            bbox = det["bbox"]
            db_insert("detections", {
                "detection_id": f"det_{uuid.uuid4().hex[:10]}",
                "image_id": result["image_id"],
                "timestamp": timestamp,
                "label": "person",
                "confidence": det.get("confidence", 0),
                "bbox_x": bbox["x"],
                "bbox_y": bbox["y"],
                "bbox_w": bbox["w"],
                "bbox_h": bbox["h"],
            })
        motion_event = {
            "event_id": f"evt_{uuid.uuid4().hex[:10]}",
            "image_id": result["image_id"],
            "camera_id": camera_id,
            "timestamp": timestamp,
            "event_type": "PERSON_MOTION_DETECTED",
            "score": round(best_score, 2),
            "severity": "WARNING",
            "explanation": reason,
            "action_hint": "Review captured image and person motion detection result.",
            "metadata": json.dumps(base_response),
        }
        db_insert("events", motion_event)
        mqtt_client.publish("events", motion_event)
        last_person_motion_at[camera_id] = time.perf_counter()
        response = {**base_response, **{
            "image_id": result["image_id"],
            "event": motion_event,
            "raw_image_url": result["raw_image_url"],
            "processed_image_url": result["processed_image_url"],
        }}
    else:
        motion_event = {
            "event_id": f"evt_{uuid.uuid4().hex[:10]}",
            "image_id": None,
            "camera_id": camera_id,
            "timestamp": now_iso(),
            "event_type": "NO_PERSON_MOTION",
            "score": round(best_score, 2),
            "severity": "NORMAL" if reason_code in {"NO_GLOBAL_MOTION", "COOLDOWN_ACTIVE"} else "WARNING",
            "explanation": reason,
            "action_hint": "Continue monitoring or enable debug=true for diagnostics.",
            "metadata": json.dumps(base_response),
        }
        db_insert("events", motion_event)
        mqtt_client.publish("events", motion_event)
        response = {**base_response, "event": motion_event}
        if debug or CFG.get("debug", {}).get("save_failed_frame", False):
            response["debug_files"] = save_motion_debug_artifacts(camera_id, best_frame, best_motion_mask, person_detections, base_response)

    append_parameter_experiment({
        "timestamp": now_iso(),
        "camera_id": camera_id,
        "method": method,
        "seconds": seconds,
        "frames_seen": frames_seen,
        "motion_score": round(best_score, 2),
        "threshold": threshold,
        "min_contour_area": min_contour_area,
        "warmup_frames": warmup_frames,
        "person_count": len(person_detections),
        "moving_person_count": len(moving_people),
        "best_overlap_ratio": round(best_overlap_ratio, 4),
        "brightness": quality.get("brightness"),
        "blur_score": quality.get("blur_score"),
        "reason_code": reason_code,
        "person_motion_detected": person_motion_detected,
    })

    await ws_manager.broadcast({"type": "motion_result", **response})
    return response

# ──────────────────────────────────────────────────────────────────────
# 14. FASTAPI APP
# ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    camera_manager.cleanup_stale(max_age_hours=1)
    camera_manager._load_from_db()
    # Register default camera if none exist
    if not camera_manager.get_all():
        camera_manager.register(CFG["camera"]["default_source"], "Default Camera")
    mqtt_client.connect()
    log.info("Lab 6 Enhanced started")
    yield
    camera_manager.release_all()
    mqtt_client.disconnect()
    log.info("Lab 6 Enhanced shutdown")

app = FastAPI(
    title="Lab 6 Enhanced - Computer Vision as IoT Sensor",
    description="SQLite, WebSocket, Multi-camera, OpenCV MOG2/KNN/HOG, MQTT, Configurable Pipeline",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/favicon.ico")
async def favicon():
    f = STATIC_DIR / "favicon.ico"
    if f.is_file():
        return FileResponse(str(f))
    return FileResponse(str(STATIC_DIR / "favicon.svg"))

@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    full = (STATIC_DIR / file_path).resolve()
    try:
        full.relative_to(STATIC_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(full), headers=NO_CACHE_HEADERS)

@app.get("/files/{file_path:path}")
async def serve_data_file(file_path: str):
    full = (ROOT / file_path).resolve()
    try:
        full.relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(full))

# ── Pages ──

@app.get("/")
def home() -> FileResponse:
    return FileResponse(INDEX_HTML, headers=NO_CACHE_HEADERS)

@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(INDEX_HTML, headers=NO_CACHE_HEADERS)

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "lab": "Lab 6 Enhanced - Computer Vision as IoT Sensor",
        "version": "2.0.0",
        "cameras": len(camera_manager.get_all()),
        "websockets": ws_manager.count,
        "detection": detector.available,
        "detection_mode": CFG["person_detection"].get("detector_mode", "opencv_hog_person"),
        "mqtt": mqtt_client.client is not None,
    }

# ── Camera Management ──

@app.get("/cameras")
def list_cameras() -> List[dict]:
    return [
        {
            "camera_id": c.camera_id,
            "source": c.source,
            "label": c.label,
            "status": c.status.value,
            "last_seen": c.last_seen,
        }
        for c in camera_manager.get_all()
    ]

@app.post("/cameras")
async def add_camera(source: str = Query(...), label: str = Query("")) -> dict:
    info = camera_manager.register(source, label)
    await ws_manager.broadcast({"type": "camera_list_updated"})
    return {"camera_id": info.camera_id, "source": info.source, "label": info.label}

@app.delete("/cameras/{camera_id}")
async def remove_camera(camera_id: str) -> dict:
    camera_manager.unregister(camera_id)
    await ws_manager.broadcast({"type": "camera_list_updated"})
    return {"status": "removed", "camera_id": camera_id}

@app.put("/cameras/{camera_id}")
async def update_camera(camera_id: str, source: Optional[str] = Query(None), label: Optional[str] = Query(None)) -> dict:
    info = camera_manager.get(camera_id)
    if not info:
        raise HTTPException(status_code=404, detail="Camera not found")
    new_source = source if source is not None else info.source
    new_label = label if label is not None else (info.label or new_source)
    info = camera_manager.update(camera_id, new_source, new_label)
    await ws_manager.broadcast({"type": "camera_list_updated"})
    return {"camera_id": info.camera_id, "source": info.source, "label": info.label}

@app.post("/cameras/cleanup")
def cleanup_cameras(max_age_hours: int = Query(24, ge=1, le=720)) -> dict:
    camera_manager.cleanup_stale(max_age_hours=max_age_hours)
    count = len(camera_manager.get_all())
    return {"status": "cleaned", "remaining_cameras": count}

@app.get("/cameras/test")
def test_camera(source: str = Query(...)) -> dict:
    parsed = camera_manager._parse_source(source)
    cap = cv2.VideoCapture(parsed)
    try:
        if not cap.isOpened():
            return {"status": "error", "message": "Cannot open camera source"}
        ret, frame = cap.read()
        if not ret or frame is None:
            return {"status": "error", "message": "Camera opened but no frame"}
        h, w = frame.shape[:2]
        return {"status": "ok", "width": w, "height": h, "message": f"Camera OK ({w}x{h})"}
    finally:
        cap.release()

@app.get("/images")
def list_images(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), camera_id: Optional[str] = Query(None)) -> dict:
    sql = "SELECT * FROM images"
    params = []
    if camera_id:
        sql += " WHERE camera_id=?"
        params.append(camera_id)
    sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = db_query_raw(sql, tuple(params))
    total = db_query_one("SELECT COUNT(*) as cnt FROM images")["cnt"]
    return {"total": total, "offset": offset, "count": len(rows), "items": rows}

@app.get("/events")
def list_events(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), event_type: Optional[str] = Query(None)) -> dict:
    sql = "SELECT * FROM events"
    params = []
    if event_type:
        if event_type in ("DETECTED", "MOTION"):
            sql += " WHERE event_type LIKE ?"
            params.append(event_type.upper() + "%")
        else:
            sql += " WHERE event_type=?"
            params.append(event_type)
    sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = db_query_raw(sql, tuple(params))
    total = db_query_one("SELECT COUNT(*) as cnt FROM events")["cnt"]
    return {"total": total, "offset": offset, "count": len(rows), "items": rows}

@app.get("/export/json")
def export_json(event_type: Optional[str] = Query(None)) -> JSONResponse:
    if event_type:
        if event_type in ("DETECTED", "MOTION"):
            rows = db_query_raw("SELECT * FROM events WHERE event_type LIKE ? ORDER BY timestamp DESC LIMIT 10000", (event_type.upper() + "%",))
        else:
            rows = db_query_raw("SELECT * FROM events WHERE event_type=? ORDER BY timestamp DESC LIMIT 10000", (event_type.upper(),))
    else:
        rows = db_query_raw("SELECT * FROM events ORDER BY timestamp DESC LIMIT 10000")
    return JSONResponse(content=rows, media_type="application/json", headers={"Content-Disposition": "attachment; filename=events.json"})

@app.get("/export/metadata/csv")
def export_metadata_csv():
    import csv, io as _io
    rows = db_query_raw("SELECT * FROM images ORDER BY timestamp DESC LIMIT 10000")
    output = _io.StringIO()
    if rows:
        w = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=metadata.csv"})

# ── Image Upload ──

MAX_UPLOAD_SIZE = 50 * 1024 * 1024

@app.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    device_id: str = "upload_client",
    camera_id: Optional[str] = Query(None),
    run_detection: bool = Query(False),
) -> Dict[str, Any]:
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    img = validate_image_bytes(data)
    return await log_image_pipeline(
        pil_to_bgr(img),
        source_type="upload",
        device_id=device_id,
        camera_id=camera_id,
        note=f"filename={file.filename}",
        run_detection=run_detection,
    )

# ── Snapshot ──

@app.get("/snapshot")
async def snapshot(
    camera_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    run_detection: bool = Query(False),
) -> Dict[str, Any]:
    # Use camera_id or source, fallback to default
    if camera_id:
        if not camera_manager.get(camera_id):
            raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
        cid = camera_id
    else:
        cams = camera_manager.get_all()
        if source:
            matching = [c for c in cams if c.source == source]
            if matching:
                cid = matching[0].camera_id
            else:
                cid = camera_manager.register(source, "Snapshot Camera").camera_id
        else:
            cid = cams[0].camera_id if cams else camera_manager.register("0", "Default").camera_id

    info = camera_manager.get(cid)
    loop = asyncio.get_event_loop()
    cap, info = await loop.run_in_executor(executor, camera_manager.open_capture, cid)

    if cap is None:
        frame = simulated_frame(0)
        source_type = "simulated"
    else:
        ok, frame = await loop.run_in_executor(executor, camera_manager.read_capture, cid, cap)
        if not ok or frame is None:
            frame = simulated_frame(0)
            source_type = "simulated_fallback"
        else:
            frame = flip_frame_if_needed(frame)
            source_type = "camera"

    return await log_image_pipeline(
        frame,
        source_type=source_type,
        device_id=f"camera:{cid}",
        camera_id=cid,
        note="snapshot",
        run_detection=run_detection,
    )

# ── Video Recording ──

@app.get("/record-video")
def record_video(
    camera_id: Optional[str] = Query(None),
    seconds: int = Query(5, ge=1, le=30),
) -> Dict[str, Any]:
    if camera_id:
        if not camera_manager.get(camera_id):
            raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
    else:
        cams = camera_manager.get_all()
        camera_id = cams[0].camera_id if cams else camera_manager.register("0", "Default").camera_id
    return record_short_video(camera_id, seconds=seconds)

# ── Motion Capture ──

@app.get("/motion-capture")
async def motion_capture_endpoint(
    camera_id: Optional[str] = Query(None),
    seconds: int = Query(CFG["motion"].get("seconds", 3), ge=1, le=30),
    method: str = Query(CFG["motion"].get("method", "mog2"), pattern="^(mog2|knn|simple)$"),
    min_area: Optional[int] = Query(None, ge=10, le=50000),
    debug: bool = Query(False),
) -> Dict[str, Any]:
    cams = camera_manager.get_all()
    if camera_id:
        if not camera_manager.get(camera_id):
            camera_id = cams[0].camera_id if cams else camera_manager.register(CFG["camera"]["default_source"], "Default").camera_id
    else:
        camera_id = cams[0].camera_id if cams else camera_manager.register("0", "Default").camera_id
    return await motion_capture(camera_id, seconds=seconds, method=method, min_area=min_area, debug=debug)

# ── Video Stream ──

@app.get("/video_feed")
async def video_feed(
    camera_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
) -> StreamingResponse:
    cams = camera_manager.get_all()
    if camera_id:
        if not camera_manager.get(camera_id):
            if cams:
                camera_id = cams[0].camera_id
            else:
                camera_id = camera_manager.register(CFG["camera"]["default_source"], "Default").camera_id
        cid = camera_id
    else:
        if source:
            matching = [c for c in cams if c.source == source]
            if matching:
                cid = matching[0].camera_id
            else:
                cid = camera_manager.register(source, "Stream Camera").camera_id
        else:
            cid = cams[0].camera_id if cams else camera_manager.register("0", "Default").camera_id
    return StreamingResponse(stream_frames(cid), media_type="multipart/x-mixed-replace; boundary=frame")

# ── Database Queries ──

@app.get("/metadata")
def get_metadata(limit: int = Query(20, ge=1, le=100), camera_id: Optional[str] = Query(None)):
    if camera_id:
        rows = db_query("SELECT * FROM images WHERE camera_id=? ORDER BY timestamp DESC", (camera_id,), limit)
    else:
        rows = db_query("SELECT * FROM images ORDER BY timestamp DESC", limit=limit)
    return {"count": len(rows), "items": rows}

@app.get("/events")
def get_events(
    limit: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
):
    conditions = []
    params = []
    if event_type:
        conditions.append("event_type=?")
        params.append(event_type.upper())
    if severity:
        conditions.append("severity=?")
        params.append(severity.upper())
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = db_query(f"SELECT * FROM events {where} ORDER BY timestamp DESC", tuple(params), limit)
    return {"count": len(rows), "items": rows}

@app.get("/detections")
def get_detections(
    limit: int = Query(20, ge=1, le=100),
    label: Optional[str] = Query(None),
):
    if label:
        rows = db_query("SELECT * FROM detections WHERE label=? ORDER BY timestamp DESC", (label,), limit)
    else:
        rows = db_query("SELECT * FROM detections ORDER BY timestamp DESC", limit=limit)
    return {"count": len(rows), "items": rows}

@app.get("/latest")
def latest():
    meta = db_query_one("SELECT * FROM images ORDER BY timestamp DESC")
    ev = db_query_one("SELECT * FROM events ORDER BY timestamp DESC")
    meta_count = db_query_one("SELECT COUNT(*) as cnt FROM images")
    ev_count = db_query_one("SELECT COUNT(*) as cnt FROM events")
    det_count = db_query_one("SELECT COUNT(*) as cnt FROM detections")
    raw_url = None
    processed_url = None
    if meta:
        raw_url = relative_url(ROOT / meta["image_path"])
        processed_url = relative_url(ROOT / meta["processed_path"])
    return {
        "latest_metadata": meta,
        "latest_event": ev,
        "raw_image_url": raw_url,
        "processed_image_url": processed_url,
        "metadata_count": meta_count["cnt"] if meta_count else 0,
        "event_count": ev_count["cnt"] if ev_count else 0,
        "detection_count": det_count["cnt"] if det_count else 0,
    }

@app.get("/stats")
def stats():
    event_stats = db_query("SELECT event_type, COUNT(*) as cnt FROM events GROUP BY event_type ORDER BY cnt DESC", limit=50)
    severity_stats = db_query("SELECT severity, COUNT(*) as cnt FROM events GROUP BY severity", limit=10)
    detection_stats = db_query("SELECT label, COUNT(*) as cnt FROM detections GROUP BY label ORDER BY cnt DESC", limit=50)
    return {
        "total_images": db_query_one("SELECT COUNT(*) as cnt FROM images")["cnt"],
        "total_events": db_query_one("SELECT COUNT(*) as cnt FROM events")["cnt"],
        "total_detections": db_query_one("SELECT COUNT(*) as cnt FROM detections")["cnt"],
        "event_by_type": event_stats,
        "event_by_severity": severity_stats,
        "detection_by_label": detection_stats,
    }

@app.get("/config")
def get_config():
    return CFG

@app.put("/config")
async def update_config(body: dict):
    ALLOWED_FILTERS = {"resize", "grayscale", "threshold", "edge", "gaussian_blur", "histogram_equalize", "sobel_x", "sobel_y"}
    validated = {}
    person_validated = {}

    if "filters" in body:
        if not isinstance(body["filters"], list) or not all(isinstance(f, str) for f in body["filters"]):
            raise HTTPException(status_code=400, detail="filters must be a list of strings")
        invalid = set(body["filters"]) - ALLOWED_FILTERS
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown filters: {', '.join(sorted(invalid))}")
        validated["filters"] = body["filters"]

    range_checks = {
        "threshold_value": (0, 255),
        "canny_low": (0, 255),
        "canny_high": (0, 255),
        "resize_width": (32, 1920),
        "resize_height": (32, 1080),
    }
    for key, (lo, hi) in range_checks.items():
        if key in body:
            val = body[key]
            if not isinstance(val, (int, float)):
                raise HTTPException(status_code=400, detail=f"{key} must be a number")
            if not lo <= val <= hi:
                raise HTTPException(status_code=400, detail=f"{key} must be between {lo} and {hi}")
            validated[key] = int(val) if isinstance(val, (int, float)) and key in ("resize_width", "resize_height") else val

    if "hog_hit_threshold" in body:
        val = body["hog_hit_threshold"]
        if not isinstance(val, (int, float)):
            raise HTTPException(status_code=400, detail="hog_hit_threshold must be a number")
        if not -1.0 <= val <= 2.0:
            raise HTTPException(status_code=400, detail="hog_hit_threshold must be between -1.0 and 2.0")
        person_validated["hog_hit_threshold"] = float(val)

    for key, val in validated.items():
        CFG["processing"][key] = val
    for key, val in person_validated.items():
        CFG["person_detection"][key] = val
    detector.cfg = CFG["person_detection"]

    updated = list(validated.keys()) + list(person_validated.keys())
    log.info(f"Config updated: processing={validated}, person_detection={person_validated}")
    return {"status": "ok", "updated": updated}

# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can send ping or commands
            if data == "ping":
                await ws.send_json({"type": "pong", "timestamp": now_iso()})
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)

# ──────────────────────────────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=CFG["server"]["host"],
        port=CFG["server"]["port"],
        reload=CFG["server"].get("reload", False),
        log_level=CFG["logging"]["level"].lower(),
    )
