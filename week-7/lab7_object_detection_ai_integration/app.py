"""
Lab 7 - Object Detection / Image AI Integration

Student-ready compact backend:
- live detection stream from laptop camera or IP camera URL
- upload image and run object detection
- snapshot from camera and run object detection
- save annotated images
- write detection_log.csv and vision_event_log.csv
- serve index.html dashboard

Run:
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
Open:
    http://127.0.0.1:8000/

Main learning path:
    camera frame -> YOLO/fallback detector -> class + confidence + bbox
    -> visual event -> log -> dashboard
"""

from __future__ import annotations

import asyncio
import csv
import json
import time
import uuid
from collections import deque
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, AsyncIterable

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                # Remove stale connection
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample_images"
INPUT_DIR = DATA_DIR / "input_images"
ANNOTATED_DIR = DATA_DIR / "annotated_images"
EVENT_SNAPSHOT_DIR = DATA_DIR / "event_snapshots"  # auto-saved frames when a WARNING/ALARM fires
OUTPUT_DIR = ROOT / "outputs"
DETECTION_CSV = OUTPUT_DIR / "detection_log.csv"
EVENT_CSV = OUTPUT_DIR / "vision_event_log.csv"
THRESHOLD_CSV = OUTPUT_DIR / "threshold_experiment_log.csv"
INDEX_HTML = ROOT / "index.html"

for folder in [SAMPLE_DIR, INPUT_DIR, ANNOTATED_DIR, EVENT_SNAPSHOT_DIR, OUTPUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Phase 1 surveillance config
DEFAULT_DWELL_SECONDS = 5.0       # object inside Zone longer than this -> DWELL_ALERT
SNAPSHOT_COOLDOWN_SEC = 3.0       # min gap between two auto-saved event snapshots
_last_snapshot_ts = 0.0

_active_zone: Optional[Dict[str, Any]] = None  # Zone configuration: {"x1": float, "y1": float, "x2": float, "y2": float, "label": str}

def calculate_iou(box1: Dict[str, int], box2: Dict[str, int]) -> float:
    x1 = max(box1["x1"], box2["x1"])
    y1 = max(box1["y1"], box2["y1"])
    x2 = min(box1["x2"], box2["x2"])
    y2 = min(box1["y2"], box2["y2"])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1["x2"] - box1["x1"]) * (box1["y2"] - box1["y1"])
    area2 = (box2["x2"] - box2["x1"]) * (box2["y2"] - box2["y1"])
    union = area1 + area2 - intersection
    if union <= 0:
        return 0.0
    return intersection / union

class Track:
    def __init__(self, track_id: int, class_name: str, bbox: Dict[str, int], confidence: float):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox = bbox
        self.confidences = [confidence]
        self.first_seen = now_iso()
        self.last_seen = now_iso()
        self.frame_count = 1
        self.missed_frames = 0
        # Dwell-time tracking (how long this object stays inside the active Zone)
        self.zone_enter_ts: Optional[float] = None
        self.dwell_alerted = False

    @property
    def avg_confidence(self) -> float:
        return round(sum(self.confidences) / len(self.confidences), 4)

    def update(self, bbox: Dict[str, int], confidence: float):
        self.bbox = bbox
        self.confidences.append(confidence)
        self.last_seen = now_iso()
        self.frame_count += 1
        self.missed_frames = 0

class ObjectTracker:
    def __init__(self, max_missed_frames: int = 5, iou_threshold: float = 0.3):
        self.max_missed_frames = max_missed_frames
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: List[Track] = []
        self.cumulative_counts: Dict[str, int] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        matched_detections = [False] * len(detections)
        matched_tracks = [False] * len(self.tracks)
        
        matches = []
        for i, det in enumerate(detections):
            for j, track in enumerate(self.tracks):
                if det["class_name"] != track.class_name:
                    continue
                iou = calculate_iou(det["bbox"], track.bbox)
                if iou >= self.iou_threshold:
                    matches.append((iou, i, j))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        for iou, det_idx, track_idx in matches:
            if not matched_detections[det_idx] and not matched_tracks[track_idx]:
                self.tracks[track_idx].update(
                    detections[det_idx]["bbox"],
                    detections[det_idx]["confidence"]
                )
                detections[det_idx]["track_id"] = self.tracks[track_idx].track_id
                matched_detections[det_idx] = True
                matched_tracks[track_idx] = True

        # Age existing tracks FIRST — while matched_tracks still lines up with self.tracks.
        # (Adding new tracks before this loop would shift indices and raise IndexError.)
        surviving: List[Track] = []
        for j, track in enumerate(self.tracks):
            if matched_tracks[j]:
                surviving.append(track)
            else:
                track.missed_frames += 1
                if track.missed_frames <= self.max_missed_frames:
                    surviving.append(track)
                else:
                    self._trigger_track_event(track, "EXIT")
        self.tracks = surviving

        # Now create tracks for unmatched detections (new objects entering the view).
        for i, det in enumerate(detections):
            if not matched_detections[i]:
                track_id = self.next_id
                self.next_id += 1
                new_track = Track(track_id, det["class_name"], det["bbox"], det["confidence"])
                self.tracks.append(new_track)
                det["track_id"] = track_id

                cls = det["class_name"]
                self.cumulative_counts[cls] = self.cumulative_counts.get(cls, 0) + 1
                self._trigger_track_event(new_track, "ENTRY")

        return detections

    def check_dwell(self, detections: List[Dict[str, Any]], dwell_seconds: float) -> List[Dict[str, Any]]:
        """Update per-track dwell timers using the in_zone flag on each detection.

        Returns a list of newly-triggered dwell alerts (one per track, fired once until
        the object leaves the zone). Annotates each detection with its current dwell time.
        """
        alerts: List[Dict[str, Any]] = []
        now = time.time()
        track_by_id = {t.track_id: t for t in self.tracks}
        for det in detections:
            tid = det.get("track_id")
            track = track_by_id.get(tid) if tid is not None else None
            if track is None:
                continue
            if det.get("in_zone"):
                if track.zone_enter_ts is None:
                    track.zone_enter_ts = now
                dwell = now - track.zone_enter_ts
                det["dwell_seconds"] = round(dwell, 1)
                det["dwell_alert"] = track.dwell_alerted
                if dwell >= dwell_seconds and not track.dwell_alerted:
                    track.dwell_alerted = True
                    det["dwell_alert"] = True
                    alerts.append({
                        "track_id": track.track_id,
                        "class_name": track.class_name,
                        "dwell_seconds": round(dwell, 1),
                        "avg_confidence": track.avg_confidence,
                    })
            else:
                # Left the zone -> reset so re-entry is a fresh dwell window
                track.zone_enter_ts = None
                track.dwell_alerted = False
                det["dwell_seconds"] = 0
                det["dwell_alert"] = False
        return alerts

    def _trigger_track_event(self, track: Track, event_direction: str):
        event_id = f"evt_{uuid.uuid4().hex[:10]}"
        timestamp = now_iso()
        event_type = f"TRACK_{event_direction}"
        severity = "INFO"
        explanation = f"Object '{track.class_name}' (ID: {track.track_id}) has {event_direction.lower()}ed the view."
        
        event_row = {
            "event_id": event_id,
            "image_id": "",
            "timestamp": timestamp,
            "event_type": event_type,
            "severity": severity,
            "class_name": track.class_name,
            "confidence": track.avg_confidence,
            "rule_used": "tracking_rule",
            "explanation": explanation,
            "action_hint": f"Log {event_direction.lower()} for track {track.track_id}.",
            "annotated_image_path": "",
        }
        append_csv(EVENT_CSV, EVENT_FIELDS, event_row)
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast({
                "event_type": "tracking_event",
                "direction": event_direction,
                "track": {
                    "track_id": track.track_id,
                    "class_name": track.class_name,
                    "avg_confidence": track.avg_confidence,
                    "first_seen": track.first_seen,
                    "last_seen": track.last_seen,
                    "frame_count": track.frame_count,
                },
                "event": event_row,
            }))
        except RuntimeError:
            pass  # No running event loop (called from sync context)
        except Exception:
            pass

tracker = ObjectTracker()

def get_track_color(track_id: int) -> Tuple[int, int, int]:
    import random
    state = random.getstate()
    random.seed(track_id)
    color = (random.randint(40, 220), random.randint(40, 220), random.randint(40, 220))
    random.setstate(state)
    return color

def draw_dashed_rectangle(img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int], color: Tuple[int, int, int], thickness: int = 2, dash_length: int = 8):
    x1, y1 = pt1
    x2, y2 = pt2
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    
    for x in range(x1, x2, dash_length * 2):
        cv2.line(img, (x, y1), (min(x + dash_length, x2), y1), color, thickness)
        cv2.line(img, (x, y2), (min(x + dash_length, x2), y2), color, thickness)
        
    for y in range(y1, y2, dash_length * 2):
        cv2.line(img, (x1, y), (x1, min(y + dash_length, y2)), color, thickness)
        cv2.line(img, (x2, y), (x2, min(y + dash_length, y2)), color, thickness)


DETECTION_FIELDS = [
    "detection_id", "image_id", "timestamp", "source_type", "model_name", "model_version",
    "threshold_used", "class_name", "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    "inference_time_ms", "annotated_image_path",
]

EVENT_FIELDS = [
    "event_id", "image_id", "timestamp", "event_type", "severity", "class_name", "confidence",
    "rule_used", "explanation", "action_hint", "annotated_image_path",
]

THRESHOLD_FIELDS = [
    "experiment_id", "timestamp", "image_id", "threshold", "num_detections", "top_class",
    "top_confidence", "inference_time_ms", "note",
]

DEFAULT_MODEL_NAME = "yolov8n.pt"  # light pretrained detector; downloaded by ultralytics on first use if internet is available
MODEL_VERSION = "lab7_yolo_nano_v1"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_SOURCE_PREFIXES = ("rtsp://", "http://", "https://")


def validate_camera_source(source: str) -> None:
    s = source.strip()
    if s.isdigit():
        return
    if any(s.startswith(p) for p in _ALLOWED_SOURCE_PREFIXES):
        return
    raise HTTPException(status_code=400, detail="Camera source must be a digit (e.g. 0) or a URL starting with rtsp:// / http:// / https://")

_detector = None
_detector_status: Dict[str, Any] = {
    "backend": "not_loaded",
    "model_name": DEFAULT_MODEL_NAME,
    "message": "Model has not been loaded yet.",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def append_csv(path: Path, fieldnames: List[str], row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def relative_url(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    try:
        rel = path.resolve().relative_to(DATA_DIR.resolve())
        return f"/files/data/{rel.as_posix()}"
    except ValueError:
        pass
    try:
        rel = path.resolve().relative_to(OUTPUT_DIR.resolve())
        return f"/files/outputs/{rel.as_posix()}"
    except ValueError:
        pass
    return None


def validate_image_bytes(data: bytes) -> Image.Image:
    try:
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}") from exc


def pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def frame_to_jpeg_bytes(frame_bgr: np.ndarray, quality: int = 80) -> bytes:
    # Quality 80 keeps detail readable while cutting encode time and payload size
    # versus the default (~95), which lowers stream latency.
    ok, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Could not encode frame as JPEG")
    return buffer.tobytes()


def create_sample_images() -> None:
    """Create simple sample images so the pipeline can run without internet or camera."""
    if any(SAMPLE_DIR.glob("*.jpg")):
        return
    img = np.full((420, 640, 3), 245, dtype=np.uint8)
    cv2.rectangle(img, (70, 110), (210, 330), (60, 140, 240), -1)
    cv2.putText(img, "sample object", (62, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.circle(img, (410, 210), 70, (80, 200, 120), -1)
    cv2.putText(img, "Lab 7 demo image", (170, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.imwrite(str(SAMPLE_DIR / "sample_objects.jpg"), img)

    img2 = np.full((420, 640, 3), 25, dtype=np.uint8)
    cv2.rectangle(img2, (90, 150), (260, 350), (180, 180, 180), -1)
    cv2.circle(img2, (460, 230), 60, (140, 140, 140), -1)
    cv2.putText(img2, "low light sample", (160, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2)
    cv2.imwrite(str(SAMPLE_DIR / "sample_low_light.jpg"), img2)


create_sample_images()


def parse_camera_source(source: str) -> Any:
    source = str(source).strip()
    return int(source) if source.isdigit() else source


def open_capture(source: str) -> Optional[cv2.VideoCapture]:
    cap = cv2.VideoCapture(parse_camera_source(source))
    if not cap.isOpened():
        return None
    try:
        # Keep only the newest frame in the driver buffer. Without this, OpenCV queues
        # several frames; when inference is slower than capture, latency grows unbounded
        # and the stream feels increasingly "behind" reality.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    return cap


def apply_flip(frame: np.ndarray, flip: int) -> np.ndarray:
    """Flip a camera frame. flip: 1=horizontal (un-mirror webcam), 0=vertical, -1=both, other=no flip."""
    if flip in (-1, 0, 1):
        return cv2.flip(frame, flip)
    return frame


def simulated_frame(counter: int = 0, width: int = 640, height: int = 360) -> np.ndarray:
    frame = np.full((height, width, 3), 245, dtype=np.uint8)
    x = 30 + (counter * 11) % max(1, width - 180)
    y = 90 + (counter * 6) % max(1, height - 180)
    cv2.rectangle(frame, (x, 100), (x + 135, 245), (45, 130, 245), -1)
    cv2.circle(frame, (width - 130, y), 48, (70, 190, 115), -1)
    cv2.putText(frame, "SIMULATED CAMERA - LAB 7", (25, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(frame, "Use source=0 for laptop camera; put object in front of camera", (25, height - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    return frame


def read_one_frame(source: str = "0", flip: int = 1) -> Tuple[np.ndarray, str]:
    cap = open_capture(source)
    if cap is None:
        return simulated_frame(0), "simulated"
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return simulated_frame(0), "simulated"
    return apply_flip(frame, flip), "camera"


def load_detector() -> Tuple[Optional[Any], Dict[str, Any]]:
    """Try to load YOLO. If unavailable, use deterministic fallback detection.

    The fallback keeps the lab runnable for smoke testing, but students should install
    ultralytics and use YOLO for the real object-detection experience.
    """
    global _detector, _detector_status
    if _detector_status["backend"] in {"ultralytics", "fallback"}:
        return _detector, _detector_status

    try:
        from ultralytics import YOLO  # type: ignore
        try:
            _detector = YOLO(DEFAULT_MODEL_NAME)
            _detector_status = {
                "backend": "ultralytics",
                "model_name": DEFAULT_MODEL_NAME,
                "model_version": MODEL_VERSION,
                "message": "YOLO nano model loaded. First run may download weights if needed.",
            }
        except Exception:
            # Try another common lightweight YOLO name for local environments.
            _detector = YOLO("yolo11n.pt")
            _detector_status = {
                "backend": "ultralytics",
                "model_name": "yolo11n.pt",
                "model_version": MODEL_VERSION,
                "message": "YOLO11 nano model loaded. First run may download weights if needed.",
            }
    except Exception as exc:
        _detector = None
        _detector_status = {
            "backend": "fallback",
            "model_name": "fallback_contour_detector",
            "model_version": "fallback_v1",
            "message": f"Ultralytics YOLO is not available or weights cannot be loaded. Fallback contour detector is active. Detail: {exc}",
        }
    return _detector, _detector_status


def parse_class_filter(classes: str = "") -> List[str]:
    return [c.strip().lower() for c in classes.split(",") if c.strip()]


def fallback_detect(frame_bgr: np.ndarray, conf: float, class_filter: List[str]) -> List[Dict[str, Any]]:
    """Simple contour-based fallback to keep the lab observable without YOLO.

    This is NOT a replacement for object detection. It only marks visually distinct
    regions as generic objects so the rest of the AIoT pipeline can be tested.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 140)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    h, w = gray.shape[:2]
    min_area = max(1200, int(0.01 * h * w))
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, bw, bh = cv2.boundingRect(contour)
        score = min(0.95, max(0.25, area / float(h * w) * 8.0))
        label = "visual_object"
        if class_filter and label not in class_filter:
            continue
        if score < conf:
            continue
        detections.append({
            "class_name": label,
            "confidence": round(float(score), 4),
            "bbox": {"x1": int(x), "y1": int(y), "x2": int(x + bw), "y2": int(y + bh)},
        })
    detections = sorted(detections, key=lambda d: d["confidence"], reverse=True)[:8]
    return detections


def yolo_detect(model: Any, frame_bgr: np.ndarray, conf: float, class_filter: List[str]) -> List[Dict[str, Any]]:
    results = model(frame_bgr, conf=conf, verbose=False)
    result = results[0]
    names = result.names if hasattr(result, "names") else {}
    detections: List[Dict[str, Any]] = []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return detections
    for box in boxes:
        xyxy = box.xyxy[0].cpu().numpy().tolist()
        cls_id = int(box.cls[0].cpu().numpy().item())
        confidence = float(box.conf[0].cpu().numpy().item())
        class_name = str(names.get(cls_id, cls_id)).lower()
        if class_filter and class_name not in class_filter:
            continue
        detections.append({
            "class_name": class_name,
            "confidence": round(confidence, 4),
            "bbox": {"x1": int(xyxy[0]), "y1": int(xyxy[1]), "x2": int(xyxy[2]), "y2": int(xyxy[3])},
        })
    return detections


def run_detection(frame_bgr: np.ndarray, conf: float = 0.35, classes: str = "") -> Tuple[List[Dict[str, Any]], Dict[str, Any], float]:
    model, status = load_detector()
    class_filter = parse_class_filter(classes)
    start = time.perf_counter()
    if status["backend"] == "ultralytics" and model is not None:
        detections = yolo_detect(model, frame_bgr, conf=conf, class_filter=class_filter)
    else:
        detections = fallback_detect(frame_bgr, conf=conf, class_filter=class_filter)
        
    h, w = frame_bgr.shape[:2]
    for det in detections:
        bbox = det["bbox"]
        dx1, dy1, dx2, dy2 = bbox["x1"] / w, bbox["y1"] / h, bbox["x2"] / w, bbox["y2"] / h
        det["in_zone"] = False
        if _active_zone:
            zx1, zy1, zx2, zy2 = _active_zone["x1"], _active_zone["y1"], _active_zone["x2"], _active_zone["y2"]
            ox1 = max(dx1, zx1)
            oy1 = max(dy1, zy1)
            ox2 = min(dx2, zx2)
            oy2 = min(dy2, zy2)
            if ox1 < ox2 and oy1 < oy2:
                det["in_zone"] = True
        else:
            det["in_zone"] = True
            
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return detections, status, elapsed_ms


def severity_from_detections(detections: List[Dict[str, Any]]) -> Tuple[str, str, str, str]:
    if not detections:
        return "NO_OBJECT_DETECTED", "NORMAL", "no_object_rule", "No object was detected above the selected confidence threshold."
    top = detections[0]
    cls = top["class_name"]
    conf = float(top["confidence"])
    
    if _active_zone and not top.get("in_zone", False):
        return "OBJECT_OUTSIDE_ZONE", "INFO", "zone_bypass_rule", f"Detected '{cls}' outside the active Zone of Interest. Severity lowered."
        
    if conf < 0.45:
        return "LOW_CONFIDENCE_REVIEW", "WARNING", "low_confidence_rule", "Detected object has low confidence; human review is recommended."
    if cls == "person":
        return "PERSON_DETECTED", "WARNING", "person_rule", "A person was detected. In AIoT, this can become a visual event for monitoring."
    if cls in {"car", "truck", "bus", "motorcycle", "bicycle"}:
        return "VEHICLE_DETECTED", "WARNING", "vehicle_rule", "A vehicle was detected. This is useful for parking, traffic or gate monitoring."
    return "OBJECT_DETECTED", "NORMAL", "generic_object_rule", "At least one object was detected above the confidence threshold."


def save_event_snapshot(annotated: np.ndarray, severity: str, event_type: str) -> Optional[Path]:
    """Persist an annotated frame to the event gallery, throttled by SNAPSHOT_COOLDOWN_SEC."""
    global _last_snapshot_ts
    now = time.time()
    if now - _last_snapshot_ts < SNAPSHOT_COOLDOWN_SEC:
        return None
    _last_snapshot_ts = now
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"evt_{severity}_{event_type}_{ts}_{uuid.uuid4().hex[:4]}.jpg"
    path = EVENT_SNAPSHOT_DIR / fname
    if not cv2.imwrite(str(path), annotated):
        return None
    return path


def draw_detections(frame_bgr: np.ndarray, detections: List[Dict[str, Any]], status: Dict[str, Any], conf: float, fps: Optional[float] = None) -> np.ndarray:
    out = frame_bgr.copy()
    h, w = out.shape[:2]

    if _active_zone:
        zx1 = int(_active_zone["x1"] * w)
        zy1 = int(_active_zone["y1"] * h)
        zx2 = int(_active_zone["x2"] * w)
        zy2 = int(_active_zone["y2"] * h)
        draw_dashed_rectangle(out, (zx1, zy1), (zx2, zy2), (0, 255, 255), 2, 8)
        cv2.putText(out, _active_zone["label"], (zx1 + 5, zy1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1, cv2.LINE_AA)

    color = (42, 180, 75) if detections else (60, 60, 220)
    for det in detections:
        bbox = det["bbox"]
        cls = det["class_name"]
        score = det["confidence"]
        track_id = det.get("track_id")
        x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]

        if track_id is not None:
            det_color = get_track_color(track_id)
            label = f"ID {track_id}: {cls} {score:.2f}"
        else:
            det_color = (50, 180, 80)
            if cls == "person":
                det_color = (50, 140, 250)
            elif score < 0.45:
                det_color = (0, 190, 255)
            label = f"{cls} {score:.2f}"

        # Dwell-time overlay + alert highlight (red, thicker) when an object lingers in the Zone
        dwell = det.get("dwell_seconds", 0)
        box_thickness = 3
        if det.get("dwell_alert"):
            det_color = (0, 0, 230)
            box_thickness = 4
            label = f"DWELL {dwell:.0f}s | " + label
        elif dwell and dwell > 0:
            label = f"{label} [{dwell:.0f}s]"

        cv2.rectangle(out, (x1, y1), (x2, y2), det_color, box_thickness)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
        cv2.rectangle(out, (x1, max(0, y1 - th - 12)), (x1 + tw + 8, y1), det_color, -1)
        cv2.putText(out, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

    header = f"{status['backend']} | conf={conf:.2f} | detections={len(detections)}"
    if fps is not None:
        header += f" | {fps:.1f} FPS"
    cv2.rectangle(out, (0, 0), (out.shape[1], 32), (255, 255, 255), -1)
    cv2.putText(out, header, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2)
    return out



def detect_and_log(frame_bgr: np.ndarray, source_type: str, device_id: str, conf: float = 0.35, classes: str = "", note: str = "") -> Dict[str, Any]:
    image_id = f"img_{uuid.uuid4().hex[:10]}"
    timestamp = now_iso()
    input_path = INPUT_DIR / f"{image_id}.jpg"
    if not cv2.imwrite(str(input_path), frame_bgr):
        raise HTTPException(status_code=500, detail="Failed to save input image. Check disk space and permissions.")

    detections, status, inference_time_ms = run_detection(frame_bgr, conf=conf, classes=classes)
    annotated = draw_detections(frame_bgr, detections, status, conf=conf)
    annotated_path = ANNOTATED_DIR / f"{image_id}_detected.jpg"
    if not cv2.imwrite(str(annotated_path), annotated):
        raise HTTPException(status_code=500, detail="Failed to save annotated image. Check disk space and permissions.")

    if detections:
        for det in detections:
            bbox = det["bbox"]
            row = {
                "detection_id": f"det_{uuid.uuid4().hex[:10]}",
                "image_id": image_id,
                "timestamp": timestamp,
                "source_type": source_type,
                "model_name": status["model_name"],
                "model_version": status["model_version"],
                "threshold_used": conf,
                "class_name": det["class_name"],
                "confidence": det["confidence"],
                "bbox_x1": bbox["x1"], "bbox_y1": bbox["y1"], "bbox_x2": bbox["x2"], "bbox_y2": bbox["y2"],
                "inference_time_ms": inference_time_ms,
                "annotated_image_path": str(annotated_path.relative_to(ROOT)),
            }
            append_csv(DETECTION_CSV, DETECTION_FIELDS, row)

    top = detections[0] if detections else {"class_name": "", "confidence": 0}
    event_type, severity, rule_used, explanation = severity_from_detections(detections)
    event_row = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "image_id": image_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "severity": severity,
        "class_name": top.get("class_name", ""),
        "confidence": top.get("confidence", 0),
        "rule_used": rule_used,
        "explanation": explanation,
        "action_hint": "Display annotated image on dashboard; do not trigger actuator without a safety rule.",
        "annotated_image_path": str(annotated_path.relative_to(ROOT)),
    }
    append_csv(EVENT_CSV, EVENT_FIELDS, event_row)

    return {
        "image_id": image_id,
        "source_type": source_type,
        "device_id": device_id,
        "model_status": status,
        "threshold_used": conf,
        "class_filter": parse_class_filter(classes),
        "num_detections": len(detections),
        "detections": detections,
        "event": event_row,
        "inference_time_ms": inference_time_ms,
        "input_image_url": relative_url(input_path),
        "annotated_image_url": relative_url(annotated_path),
        "note": note,
    }


async def stream_detect_frames(source: str = "0", conf: float = 0.35, classes: str = "", flip: int = 1, dwell: float = DEFAULT_DWELL_SECONDS) -> AsyncIterable[bytes]:
    cap = open_capture(source)
    counter = 0
    prev_active_ids: set = set()
    frame_times: deque = deque(maxlen=20)  # for real serving-FPS estimate
    fps = 0.0
    try:
        while True:
            frame_times.append(time.time())
            if len(frame_times) >= 2:
                span = frame_times[-1] - frame_times[0]
                fps = (len(frame_times) - 1) / span if span > 0 else 0.0

            if cap is None:
                frame = simulated_frame(counter)
            else:
                ok, frame = cap.read()
                if not ok or frame is None:
                    # Dead capture — release and fall back to simulated frames permanently
                    cap.release()
                    cap = None
                    frame = simulated_frame(counter)
                else:
                    frame = apply_flip(frame, flip)

            dwell_alerts: List[Dict[str, Any]] = []
            try:
                # Offload the blocking YOLO inference to a worker thread so the asyncio
                # event loop stays free to flush already-encoded frames to the client.
                # Running it inline freezes the loop for the whole inference (~tens of ms
                # on CPU), which is the main cause of choppy/laggy streaming.
                detections, status, elapsed_ms = await asyncio.to_thread(run_detection, frame, conf, classes)
                detections = tracker.update(detections)
                if _active_zone:
                    dwell_alerts = tracker.check_dwell(detections, dwell)
                annotated = draw_detections(frame, detections, status, conf=conf, fps=fps)
            except Exception:
                detections, elapsed_ms = [], 0.0
                status = {"backend": _detector_status.get("backend", "error")}
                annotated = frame.copy() if frame is not None else simulated_frame(counter)

            current_active_ids = {det["track_id"] for det in detections if "track_id" in det}

            # Auto-save a snapshot + log + broadcast for each new dwell alert
            for alert in dwell_alerts:
                snap = save_event_snapshot(annotated, "WARNING", "DWELL_ALERT")
                alert_row = {
                    "event_id": f"evt_{uuid.uuid4().hex[:10]}",
                    "image_id": "",
                    "timestamp": now_iso(),
                    "event_type": "DWELL_ALERT",
                    "severity": "WARNING",
                    "class_name": alert["class_name"],
                    "confidence": alert["avg_confidence"],
                    "rule_used": "dwell_time_rule",
                    "explanation": f"Object '{alert['class_name']}' (ID {alert['track_id']}) stayed in the Zone for {alert['dwell_seconds']}s.",
                    "action_hint": "Raise a monitoring alert; consider notifying an operator.",
                    "annotated_image_path": str(snap.relative_to(ROOT)) if snap else "",
                }
                append_csv(EVENT_CSV, EVENT_FIELDS, alert_row)
                try:
                    await manager.broadcast({
                        "event_type": "alert_event",
                        "alert_type": "DWELL_ALERT",
                        "severity": "WARNING",
                        "track": alert,
                        "snapshot_url": relative_url(snap) if snap else None,
                        "event": alert_row,
                    })
                except Exception:
                    pass

            if manager.active_connections:
                try:
                    current_stats = get_stats_data()
                except Exception:
                    current_stats = {}

                top = detections[0] if detections else {"class_name": "", "confidence": 0}
                event_type, severity, rule_used, explanation = severity_from_detections(detections)

                # Auto-save annotated frame to the event gallery when a WARNING fires
                # (throttled by SNAPSHOT_COOLDOWN_SEC, shared with dwell snapshots).
                snap_path = ""
                if severity == "WARNING":
                    snap = save_event_snapshot(annotated, severity, event_type)
                    if snap:
                        snap_path = str(snap.relative_to(ROOT))

                event_row = {
                    "event_id": f"evt_stream_{uuid.uuid4().hex[:6]}",
                    "image_id": f"img_stream_{counter}",
                    "timestamp": now_iso(),
                    "event_type": event_type,
                    "severity": severity,
                    "class_name": top.get("class_name", ""),
                    "confidence": top.get("confidence", 0),
                    "rule_used": rule_used,
                    "explanation": explanation,
                    "action_hint": "Live stream event.",
                    "annotated_image_path": snap_path,
                }

                if current_active_ids != prev_active_ids or counter % 5 == 0:
                    try:
                        await manager.broadcast({
                            "event_type": "detection_update",
                            "detections": detections,
                            "event": event_row,
                            "inference_time_ms": elapsed_ms,
                            "fps": round(fps, 1),
                            "stats": current_stats,
                            "model_status": status,
                            "threshold_used": conf,
                        })
                    except Exception:
                        pass

            prev_active_ids = current_active_ids
            try:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_to_jpeg_bytes(annotated) + b"\r\n"
            except Exception:
                break
            counter += 1
            # Small yield to the event loop. Inference (in the worker thread) already
            # paces the loop; a large sleep here would only cap the frame rate and add lag.
            await asyncio.sleep(0.01)
    finally:
        if cap is not None:
            cap.release()


_stats_cache = {}
_stats_last_updated = 0.0

def get_stats_data() -> Dict[str, Any]:
    global _stats_cache, _stats_last_updated
    current_time = time.time()
    if current_time - _stats_last_updated < 2.0 and _stats_cache:
        return _stats_cache
        
    detections = read_csv(DETECTION_CSV)
    events = read_csv(EVENT_CSV)
    
    det_by_min = {}
    for d in detections:
        ts = d.get("timestamp", "")
        if len(ts) >= 16:
            minute_str = ts[:16]
            det_by_min[minute_str] = det_by_min.get(minute_str, 0) + 1
    sorted_mins = sorted(det_by_min.keys())[-10:]
    detections_per_minute = [{"minute": m, "count": det_by_min[m]} for m in sorted_mins]
    
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for d in detections:
        try:
            conf = float(d.get("confidence", 0.0))
            if conf < 0.2: buckets["0.0-0.2"] += 1
            elif conf < 0.4: buckets["0.2-0.4"] += 1
            elif conf < 0.6: buckets["0.4-0.6"] += 1
            elif conf < 0.8: buckets["0.6-0.8"] += 1
            else: buckets["0.8-1.0"] += 1
        except ValueError:
            pass
            
    class_counts = {}
    for d in detections:
        cls = d.get("class_name", "")
        if cls:
            class_counts[cls] = class_counts.get(cls, 0) + 1
    top_classes = [{"class": c, "count": count} for c, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    latencies = []
    for d in detections:
        try:
            latencies.append(float(d.get("inference_time_ms", 0.0)))
        except ValueError:
            pass
    avg_inference_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    
    severity_counts = {}
    for e in events:
        sev = e.get("severity", "")
        if sev:
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
    _stats_cache = {
        "detections_per_minute": detections_per_minute,
        "confidence_distribution": buckets,
        "top_classes": top_classes,
        "avg_inference_ms": avg_inference_ms,
        "event_severity_breakdown": severity_counts,
        "cumulative_tracking_counts": tracker.cumulative_counts
    }
    _stats_last_updated = current_time
    return _stats_cache


app = FastAPI(title="Lab 7 - Object Detection / Image AI Integration", description="Live camera object detection, annotated image, detection log, visual event and dashboard.")
app.mount("/files/data", StaticFiles(directory=str(DATA_DIR)), name="files_data")
app.mount("/files/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="files_outputs")


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "lab": "Lab 7 - Object Detection / Image AI Integration", "outputs": {"detection_log": str(DETECTION_CSV.relative_to(ROOT)), "vision_event_log": str(EVENT_CSV.relative_to(ROOT))}}


@app.get("/model-info")
def model_info() -> Dict[str, Any]:
    _, status = load_detector()
    return {"task": "object_detection", "status": status, "default_threshold": 0.35, "main_source": "laptop camera source=0", "note": "If backend=fallback, install ultralytics and allow the YOLO nano weights to download for real object detection."}


@app.get("/stats")
def get_stats_endpoint() -> Dict[str, Any]:
    return get_stats_data()


@app.post("/zone")
def set_zone(zone: Dict[str, Any]) -> Dict[str, Any]:
    global _active_zone
    _active_zone = {
        "x1": min(max(float(zone.get("x1", 0.0)), 0.0), 1.0),
        "y1": min(max(float(zone.get("y1", 0.0)), 0.0), 1.0),
        "x2": min(max(float(zone.get("x2", 1.0)), 0.0), 1.0),
        "y2": min(max(float(zone.get("y2", 1.0)), 0.0), 1.0),
        "label": str(zone.get("label", "Zone of Interest")),
    }
    return {"status": "success", "zone": _active_zone}


@app.delete("/zone")
def delete_zone() -> Dict[str, Any]:
    global _active_zone
    _active_zone = None
    return {"status": "success", "message": "Zone cleared"}


@app.get("/video_feed")
def video_feed(source: str = Query("0"), conf: float = Query(0.35, ge=0.01, le=0.99), classes: str = Query(""), flip: int = Query(1), dwell: float = Query(DEFAULT_DWELL_SECONDS, ge=1.0, le=120.0)) -> StreamingResponse:
    validate_camera_source(source)
    return StreamingResponse(stream_detect_frames(source=source, conf=conf, classes=classes, flip=flip, dwell=dwell), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/event-snapshots")
def event_snapshots(limit: int = Query(12, ge=1, le=60)) -> Dict[str, Any]:
    files = sorted(EVENT_SNAPSHOT_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    items = []
    for p in files:
        # filename: evt_{severity}_{event_type}_{YYYYmmdd}_{HHMMSS}_{hex}.jpg
        parts = p.stem.split("_")
        severity = parts[1] if len(parts) > 1 else ""
        event_type = parts[2] if len(parts) > 2 else ""
        items.append({
            "filename": p.name,
            "url": relative_url(p),
            "severity": severity,
            "event_type": event_type,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return {"count": len(items), "items": items}


@app.get("/snapshot-detect")
def snapshot_detect(source: str = Query("0"), conf: float = Query(0.35, ge=0.01, le=0.99), classes: str = Query(""), flip: int = Query(1)) -> Dict[str, Any]:
    validate_camera_source(source)
    frame, source_type = read_one_frame(source, flip=flip)
    return detect_and_log(frame, source_type=source_type, device_id=f"camera:{source}", conf=conf, classes=classes, note="snapshot-detect")


@app.post("/upload-detect")
async def upload_detect(file: UploadFile = File(...), conf: float = Query(0.35, ge=0.01, le=0.99), classes: str = Query("")) -> Dict[str, Any]:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    img = validate_image_bytes(data)
    return detect_and_log(pil_to_bgr(img), source_type="upload", device_id="upload_client", conf=conf, classes=classes, note=f"filename={file.filename}")


@app.get("/detect-sample")
def detect_sample(sample: str = Query("sample_objects.jpg"), conf: float = Query(0.25, ge=0.01, le=0.99), classes: str = Query("")) -> Dict[str, Any]:
    path = (SAMPLE_DIR / sample).resolve()
    try:
        path.relative_to(SAMPLE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid sample path.")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Sample image not found: {sample}")
    frame = cv2.imread(str(path))
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not read sample image")
    return detect_and_log(frame, source_type="sample", device_id="sample_image", conf=conf, classes=classes, note=f"sample={sample}")


@app.get("/threshold-experiment")
def threshold_experiment(sample: str = Query("sample_objects.jpg"), classes: str = Query("")) -> Dict[str, Any]:
    path = (SAMPLE_DIR / sample).resolve()
    try:
        path.relative_to(SAMPLE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid sample path.")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Sample image not found: {sample}")
    frame = cv2.imread(str(path))
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not read sample image")
    experiment_id = f"exp_{uuid.uuid4().hex[:10]}"
    rows = []
    for threshold in [0.25, 0.50, 0.70]:
        result = detect_and_log(frame, source_type="threshold_experiment", device_id="sample_image", conf=threshold, classes=classes, note=f"experiment_id={experiment_id}")
        top = result["detections"][0] if result["detections"] else {"class_name": "", "confidence": 0}
        row = {
            "experiment_id": experiment_id,
            "timestamp": now_iso(),
            "image_id": result["image_id"],
            "threshold": threshold,
            "num_detections": result["num_detections"],
            "top_class": top.get("class_name", ""),
            "top_confidence": top.get("confidence", 0),
            "inference_time_ms": result["inference_time_ms"],
            "note": "Compare how threshold changes number of detections.",
        }
        append_csv(THRESHOLD_CSV, THRESHOLD_FIELDS, row)
        rows.append(row)
    return {"experiment_id": experiment_id, "items": rows}


@app.get("/detections")
def detections(limit: int = Query(30, ge=1, le=500)) -> Dict[str, Any]:
    rows = read_csv(DETECTION_CSV)
    return {"count": len(rows), "items": rows[-limit:]}


@app.get("/vision-events")
def vision_events(limit: int = Query(30, ge=1, le=500)) -> Dict[str, Any]:
    rows = read_csv(EVENT_CSV)
    return {"count": len(rows), "items": rows[-limit:]}


@app.get("/latest")
def latest() -> Dict[str, Any]:
    events = read_csv(EVENT_CSV)
    detections = read_csv(DETECTION_CSV)
    latest_event = events[-1] if events else None
    annotated_url = None
    if latest_event and latest_event.get("annotated_image_path"):
        annotated_url = relative_url(ROOT / latest_event["annotated_image_path"])
    return {
        "latest_event": latest_event,
        "latest_detections": detections[-10:],
        "event_count": len(events),
        "detection_count": len(detections),
        "annotated_image_url": annotated_url,
    }


if __name__ == "__main__":
    create_sample_images()
    sample = cv2.imread(str(SAMPLE_DIR / "sample_objects.jpg"))
    result = detect_and_log(sample, source_type="script", device_id="local_smoke", conf=0.25, note="python app.py smoke test")
    print(json.dumps(result, indent=2, ensure_ascii=False))
