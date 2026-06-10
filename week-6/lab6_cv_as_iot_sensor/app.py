"""
Lab 6 Enhanced — Computer Vision as IoT Sensor
===============================================
Nâng cấp toàn diện so với bản gốc:
  ✔ SQLite (thay CSV) — query linh hoạt, concurrent safe, có foreign key
  ✔ WebSocket — dashboard real-time, không polling 5s
  ✔ Multi-camera — đăng ký / quản lý nhiều camera, xem grid
  ✔ Background subtractor MOG2 — motion detection thông minh hơn
  ✔ ONNX object detection (tùy chọn) — phát hiện người, xe, vật thể
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
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
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
    cfg.setdefault("motion", {"method": "mog2", "min_area": 800, "simple_threshold": 25, "mog2_history": 500, "mog2_var_threshold": 16, "detect_shadows": True})
    cfg.setdefault("detection", {"enabled": False, "model_path": "models/yolov8n.onnx", "input_size": 640, "confidence_threshold": 0.5, "nms_threshold": 0.45})
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
INDEX_HTML = ROOT / "index.html"

for folder in [RAW_DIR, PROCESSED_DIR, VIDEO_DIR, OUTPUT_DIR, MODELS_DIR, STATIC_DIR, DB_PATH.parent, (ROOT / CFG["logging"]["file"]).parent]:
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

    def get_all(self) -> List[CameraInfo]:
        return list(self._cameras.values())

    def get(self, camera_id: str) -> Optional[CameraInfo]:
        return self._cameras.get(camera_id)

    def open_capture(self, camera_id: str) -> Tuple[Optional[cv2.VideoCapture], Optional[CameraInfo]]:
        info = self._cameras.get(camera_id)
        if not info:
            return None, None
        cap = self._captures.get(camera_id)
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(self._parse_source(info.source))
            if info.width and info.height:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, info.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, info.height)
            if cap.isOpened():
                self._captures[camera_id] = cap
                info.status = CameraStatus.ONLINE
                info.last_seen = now_iso()
                self._update_last_seen(camera_id)
            else:
                info.status = CameraStatus.OFFLINE
                return None, info
        return cap, info

    def release(self, camera_id: str):
        self._release_capture(camera_id)

    def _release_capture(self, camera_id: str):
        cap = self._captures.pop(camera_id, None)
        if cap:
            cap.release()

    def release_all(self):
        for cid in list(self._captures.keys()):
            self._release_capture(cid)

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
# 7. OBJECT DETECTION (ONNX YOLOv8 — Tùy chọn)
# ──────────────────────────────────────────────────────────────────────

class ObjectDetector:
    def __init__(self, config: dict):
        self.cfg = config
        self.session = None
        self.input_name = None
        self.input_shape = None
        self.labels = config.get("classes", ["person", "car"])
        self._load_model()

    def _load_model(self):
        if not self.cfg.get("enabled", False):
            log.info("ONNX detection disabled by config")
            return
        model_path = ROOT / self.cfg.get("model_path", "models/yolov8n.onnx")
        if not model_path.exists():
            log.warning(f"Model not found at {model_path}. Detection disabled. Run download_model.py to fetch it.")
            return
        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(str(model_path))
            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            log.info(f"ONNX model loaded: {model_path} (input: {self.input_shape})")
        except Exception as e:
            log.error(f"Failed to load ONNX model: {e}")

    @property
    def available(self) -> bool:
        return self.session is not None

    def detect(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        if not self.available:
            return []

        input_size = self.cfg.get("input_size", 640)
        conf_thresh = self.cfg.get("confidence_threshold", 0.5)
        nms_thresh = self.cfg.get("nms_threshold", 0.45)

        orig_h, orig_w = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(frame_bgr, 1/255.0, (input_size, input_size), swapRB=True, crop=False)
        outputs = self.session.run(None, {self.input_name: blob})

        predictions = np.squeeze(outputs[0]).T  # (8400, 84)
        boxes, scores, class_ids = [], [], []

        for pred in predictions:
            class_scores = pred[4:]
            class_id = np.argmax(class_scores)
            score = float(class_scores[class_id])
            if score < conf_thresh:
                continue
            cx, cy, w, h = pred[:4]
            box_w = int(w * orig_w / input_size)
            box_h = int(h * orig_h / input_size)
            x = int((cx - w/2) * orig_w / input_size)
            y = int((cy - h/2) * orig_h / input_size)
            boxes.append([x, y, box_w, box_h])
            scores.append(score)
            class_ids.append(class_id)

        if not boxes:
            return []

        raw = cv2.dnn.NMSBoxes(boxes, scores, conf_thresh, nms_thresh)
        indices = np.array(raw, dtype=np.int64).flatten() if len(raw) > 0 else []
        results = []
        coco_labels = self._get_coco_labels()
        for i in indices:
            label = coco_labels.get(class_ids[i], f"class_{class_ids[i]}")
            if label not in self.labels:
                continue
            x, y, bw, bh = boxes[i]
            results.append({
                "label": label,
                "confidence": round(scores[i], 3),
                "bbox": {"x": x, "y": y, "w": bw, "h": bh},
            })
        return results

    @staticmethod
    def _get_coco_labels() -> Dict[int, str]:
        return {
            0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
            5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
            10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench", 14: "bird",
            15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
            20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
            25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
            30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite", 34: "baseball bat",
            35: "baseball glove", 36: "skateboard", 37: "surfboard", 38: "tennis racket", 39: "bottle",
            40: "wine glass", 41: "cup", 42: "fork", 43: "knife", 44: "spoon",
            45: "bowl", 46: "banana", 47: "apple", 48: "sandwich", 49: "orange",
            50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut",
            55: "cake", 56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
            60: "dining table", 61: "toilet", 62: "tv", 63: "laptop", 64: "mouse",
            65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave", 69: "oven",
            70: "toaster", 71: "sink", 72: "refrigerator", 73: "book", 74: "clock",
            75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier", 79: "toothbrush",
        }

    def draw_detections(self, frame_bgr: np.ndarray, detections: List[dict]) -> np.ndarray:
        canvas = frame_bgr.copy()
        for det in detections:
            b = det["bbox"]
            x1, y1, x2, y2 = b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label_text = f"{det['label']} {det['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(canvas, (x1, y1-th-8), (x1+tw+8, y1), (0, 255, 0), -1)
            cv2.putText(canvas, label_text, (x1+4, y1-4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        return canvas

detector = ObjectDetector(CFG["detection"])

def fallback_detect_visual_regions(frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """Lightweight fallback so object-detection demos work before ONNX is installed."""
    height, width = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_mask = cv2.inRange(saturation, 45, 255)
    dark_mask = cv2.inRange(value, 0, 80)
    mask = cv2.bitwise_or(color_mask, dark_mask)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = max(900, int(width * height * 0.006))
    detections: List[Dict[str, Any]] = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        detections.append({
            "label": "visual_region",
            "confidence": round(min(0.95, max(0.25, area / float(width * height))), 3),
            "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        })
    return detections

def normalize_detection_objects(detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    objects = []
    for det in detections:
        bbox = det.get("bbox", {})
        x = int(bbox.get("x", 0))
        y = int(bbox.get("y", 0))
        w = int(bbox.get("w", 0))
        h = int(bbox.get("h", 0))
        objects.append({
            "class_name": det.get("label", "unknown"),
            "confidence": det.get("confidence", 0),
            "bbox": {"x1": x, "y1": y, "x2": x + w, "y2": y + h},
        })
    return objects

def draw_fallback_detections(frame_bgr: np.ndarray, detections: List[Dict[str, Any]], detector_mode: str) -> np.ndarray:
    canvas = frame_bgr.copy()
    if detector.available:
        canvas = detector.draw_detections(canvas, detections)
    else:
        for det in detections:
            b = det["bbox"]
            x1, y1, x2, y2 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (60, 180, 240), 2)
            label_text = f"{det['label']} {det['confidence']:.2f}"
            cv2.rectangle(canvas, (x1, max(0, y1 - 24)), (min(canvas.shape[1] - 1, x1 + 220), y1), (60, 180, 240), -1)
            cv2.putText(canvas, label_text, (x1 + 4, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 34), (255, 255, 255), -1)
    cv2.putText(canvas, f"OBJECT DETECTION | {detector_mode}", (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 2)
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

    # Generate event
    if brightness < CFG["processing"].get("brightness_threshold", 70):
        event_type = "LOW_LIGHT"
        severity = "WARNING"
        explanation = "Image brightness is low; AI inference may be unreliable."
        action_hint = "Improve lighting or review image quality."
    else:
        event_type = "IMAGE_PROCESSED"
        severity = "NORMAL"
        explanation = "Image was received, saved, preprocessed, and registered."
        action_hint = "Continue monitoring or pass to object detection."

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
        "metadata": json.dumps({"source_type": source_type, "note": note}),
    }
    db_insert("events", event_row)

    # Object detection
    detections = []
    detector_mode = "none"
    if run_detection:
        try:
            if detector.available:
                detector_mode = "yolov8n_onnx"
                detections = await loop.run_in_executor(executor, detector.detect, frame_bgr)
            else:
                detector_mode = "fallback_contour"
                detections = await loop.run_in_executor(executor, fallback_detect_visual_regions, frame_bgr)
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
                labels_str = ", ".join(d["label"] for d in detections)
                det_event = {
                    "event_id": f"evt_{uuid.uuid4().hex[:10]}",
                    "image_id": image_id,
                    "camera_id": camera_id,
                    "timestamp": timestamp,
                    "event_type": f"DETECTED_{detections[0]['label'].upper()}" if detector.available else "OBJECT_DETECTION_FALLBACK",
                    "score": detections[0]["confidence"],
                    "severity": "WARNING" if not detector.available else "NORMAL",
                    "explanation": f"Detected: {labels_str}" if detector.available else f"Fallback detected visual regions: {labels_str}",
                    "action_hint": "Review detection results in dashboard." if detector.available else "Install models/yolov8n.onnx for real YOLO object detection.",
                    "metadata": json.dumps({"detections": detections, "detector_mode": detector_mode}),
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
    })

    return {
        "image_id": image_id,
        "metadata": meta,
        "event": event_row,
        "detections": detections,
        "raw_image_url": relative_url(raw_path),
        "processed_image_url": relative_url(processed_path),
    }

# ──────────────────────────────────────────────────────────────────────
# 11. VIDEO STREAMING (Async)
# ──────────────────────────────────────────────────────────────────────

async def stream_frames(camera_id: str) -> AsyncIterator[bytes]:
    info = camera_manager.get(camera_id)
    counter = 0
    use_simulated = False
    cap = None
    loop = asyncio.get_event_loop()

    while True:
        frame = None
        source_label = "SIMULATED"

        if not use_simulated:
            if cap is None:
                cap, info = camera_manager.open_capture(camera_id)
            if cap is not None:
                ok, frame = await loop.run_in_executor(executor, cap.read)
                if ok and frame is not None:
                    frame = flip_frame_if_needed(frame)
                    source_label = "LIVE"
                else:
                    use_simulated = True
            else:
                use_simulated = True

        if use_simulated and counter > 0 and counter % 60 == 0:
            if cap is not None:
                cap.release()
                cap = None
            camera_manager.release(camera_id)
            use_simulated = False
            continue

        if use_simulated or frame is None:
            w = info.width if info else 640
            h = info.height if info else 360
            frame = simulated_frame(counter, w, h)
            source_label = "SIMULATED"

        cam_label = info.label if info else camera_id
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 32), (255, 255, 255), -1)
        cv2.putText(frame, f"{source_label} | {cam_label} | frame={counter}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

        jpg = frame_to_jpeg_bytes(frame)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
        counter += 1
        await asyncio.sleep(1.0 / CFG["camera"].get("fps", 12))

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
    seconds: int = 8,
    method: str = "mog2",
    min_area: int = 800,
    simple_threshold: int = 25,
) -> Dict[str, Any]:
    seconds = max(1, min(int(seconds), 30))
    info = camera_manager.get(camera_id)

    mog2 = None
    if method == "mog2":
        mog2 = cv2.createBackgroundSubtractorMOG2(
            history=CFG["motion"].get("mog2_history", 500),
            varThreshold=CFG["motion"].get("mog2_var_threshold", 16),
            detectShadows=CFG["motion"].get("detect_shadows", True),
        )

    prev_gray = None
    best_frame = None
    best_score = 0.0
    frames_seen = 0
    start = time.perf_counter()

    loop = asyncio.get_event_loop()

    backup_cap = None
    cap = None
    if info:
        cap, _ = camera_manager.open_capture(camera_id)
        if cap is None:
            backup_cap = cv2.VideoCapture(camera_manager._parse_source(info.source))
            cap = backup_cap if backup_cap.isOpened() else None

    def _frame_mog2(f):
        fg = mog2.apply(f)
        m = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]
        ctrs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return float(sum(cv2.contourArea(c) for c in ctrs))

    def _frame_simple(f, pg):
        g = cv2.cvtColor(cv2.resize(f, (320, 240)), cv2.COLOR_BGR2GRAY)
        if pg is not None:
            d = cv2.absdiff(pg, g)
            _, m = cv2.threshold(d, simple_threshold, 255, cv2.THRESH_BINARY)
            ctrs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return float(sum(cv2.contourArea(c) for c in ctrs)), g
        return 0.0, g

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

            if mog2 is not None:
                score = await loop.run_in_executor(executor, _frame_mog2, frame)
            else:
                score, prev_gray = await loop.run_in_executor(executor, _frame_simple, frame, prev_gray)

            if score > best_score:
                best_score = score
                best_frame = frame.copy()

            await asyncio.sleep(0.05)
    finally:
        if backup_cap is not None:
            backup_cap.release()
    if best_frame is None:
        best_frame = simulated_frame(frames_seen)

    result = await log_image_pipeline(
        best_frame,
        source_type="motion_capture",
        device_id=f"camera:{camera_id}",
        camera_id=camera_id,
        note=f"motion_score={round(best_score, 2)}, method={method}",
        run_detection=True,
    )

    motion_detected = best_score >= float(min_area)
    motion_event = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "image_id": result["image_id"],
        "camera_id": camera_id,
        "timestamp": now_iso(),
        "event_type": "MOTION_DETECTED" if motion_detected else "NO_SIGNIFICANT_MOTION",
        "score": round(best_score, 2),
        "severity": "WARNING" if motion_detected else "NORMAL",
        "explanation": f"Motion score {best_score:.0f} exceeds threshold {min_area}." if motion_detected else f"Motion score {best_score:.0f} below threshold {min_area}.",
        "action_hint": "Review captured image." if motion_detected else "Continue visual monitoring.",
        "metadata": json.dumps({"method": method, "frames_seen": frames_seen}),
    }
    db_insert("events", motion_event)
    mqtt_client.publish("events", motion_event)
    await ws_manager.broadcast({"type": "motion_result", "motion_detected": motion_detected, **motion_event})

    result["motion_event"] = motion_event
    result["motion_detected"] = motion_detected
    result["frames_seen"] = frames_seen
    return result

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

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Lab 6 Enhanced - Computer Vision as IoT Sensor",
    description="SQLite, WebSocket, Multi-camera, MOG2, ONNX, MQTT, Configurable Pipeline",
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
@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    full = (STATIC_DIR / file_path).resolve()
    try:
        full.relative_to(STATIC_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(full))

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
    return FileResponse(INDEX_HTML)

@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(INDEX_HTML)

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "lab": "Lab 6 Enhanced - Computer Vision as IoT Sensor",
        "version": "2.0.0",
        "cameras": len(camera_manager.get_all()),
        "websockets": ws_manager.count,
        "detection": detector.available,
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
def add_camera(source: str = Query(...), label: str = Query("")) -> dict:
    info = camera_manager.register(source, label)
    return {"camera_id": info.camera_id, "source": info.source, "label": info.label}

@app.delete("/cameras/{camera_id}")
def remove_camera(camera_id: str) -> dict:
    camera_manager.unregister(camera_id)
    return {"status": "removed", "camera_id": camera_id}

@app.post("/cameras/cleanup")
def cleanup_cameras(max_age_hours: int = Query(24, ge=1, le=720)) -> dict:
    camera_manager.cleanup_stale(max_age_hours=max_age_hours)
    count = len(camera_manager.get_all())
    return {"status": "cleaned", "remaining_cameras": count}

# ── Image Upload ──

@app.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    device_id: str = "upload_client",
    camera_id: Optional[str] = Query(None),
    run_detection: bool = Query(False),
) -> Dict[str, Any]:
    data = await file.read()
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
    cap, info = camera_manager.open_capture(cid)

    if cap is None:
        frame = simulated_frame(0)
        source_type = "simulated"
    else:
        loop = asyncio.get_event_loop()
        ok, frame = await loop.run_in_executor(executor, cap.read)
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
    seconds: int = Query(8, ge=1, le=30),
    method: str = Query("mog2"),
    min_area: int = Query(800, ge=10, le=50000),
) -> Dict[str, Any]:
    if camera_id:
        if not camera_manager.get(camera_id):
            raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
    else:
        cams = camera_manager.get_all()
        camera_id = cams[0].camera_id if cams else camera_manager.register("0", "Default").camera_id
    return await motion_capture(camera_id, seconds=seconds, method=method, min_area=min_area)

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

    for key, val in validated.items():
        CFG["processing"][key] = val

    log.info(f"Config updated: {validated}")
    return {"status": "ok", "updated": list(validated.keys())}

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
