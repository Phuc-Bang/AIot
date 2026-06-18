from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError

from app.schemas import AnomalyRequest, ForecastRequest, RiskRequest
from app.sensor_inference import detect_anomaly_ml, forecast_ml, risk_from_forecast
from app.vision_inference import VisionClassifier
from app.logging_utils import append_csv_log

MODEL_DIR = os.getenv("MODEL_DIR", "models")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
VISION_MODEL_PATH = os.getenv("VISION_MODEL_PATH", "models/vision/resnet18-v1-7.onnx")
VISION_LABELS_PATH = os.getenv("VISION_LABELS_PATH", "models/vision/imagenet_classes.txt")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

app = FastAPI(
    title="Lab 5 - Dockerized Multi-Model AIoT Inference Service (Upgraded)",
    version="2.0.0",
    description=(
        "AIoT inference service with ML-based sensor models (Isolation Forest + Linear Regression), "
        "an upgraded ResNet18 ONNX vision model, "
        "and a simple browser UI for image upload."
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_vision_model: VisionClassifier | None = None


def _get_vision_model() -> VisionClassifier:
    global _vision_model
    if _vision_model is None:
        _vision_model = VisionClassifier(VISION_MODEL_PATH, VISION_LABELS_PATH)
    return _vision_model


def _decode_uploaded_image(file_bytes: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Cannot decode image. Please upload a valid image file.")


async def _read_image_upload(file: UploadFile) -> tuple[bytes, Image.Image]:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max upload size is {MAX_UPLOAD_BYTES} bytes.")
    return content, _decode_uploaded_image(content)


@app.get("/")
def root():
    return {
        "service": "Lab 5 Dockerized Multi-Model AIoT Inference Service",
        "docs": "/docs",
        "image_upload_demo": "/classify-image-demo",
        "endpoints": [
            "/health", "/model-info", "/detect-anomaly", "/forecast", "/predict-risk",
            "/vision/model-info", "/classify-image", "/classify-image-annotated", "/classify-image-demo"
        ]
    }


@app.get("/health")
def health():
    return {
        "service_status": "ok",
        "model_dir": MODEL_DIR,
        "output_dir": OUTPUT_DIR,
        "vision_model_loaded": _get_vision_model().loaded
    }


@app.get("/model-info")
def model_info():
    return {
        "service_type": "multi_model_aiot_inference",
        "sensor_models": {
            "anomaly": "modified_zscore_mad_v1",
            "forecast": "linear_regression_numpy_v1"
        },
        "vision_model": _get_vision_model().info(),
        "model_format_learning_path": [
            "Start with framework-native models: PyTorch .pt/.pth and TensorFlow .keras/SavedModel.",
            "Then convert or export to portable inference formats such as ONNX or lightweight edge formats such as TFLite.",
            "Use Docker to package runtime, dependencies, model files, and API behavior into a reproducible service."
        ],
        "note": "Optimized: Sensor models use numpy-only ML (modified Z-score + linear regression). Vision model upgraded from SqueezeNet to ResNet18. No scikit-learn/scipy dependency."
    }


@app.post("/detect-anomaly")
def detect_anomaly(payload: AnomalyRequest):
    result = detect_anomaly_ml(payload.current_value, payload.recent_values, payload.threshold_z)
    append_csv_log(Path(OUTPUT_DIR) / "service_log.csv", {
        "endpoint": "/detect-anomaly",
        "target": payload.target,
        "status": "ok",
        "summary": result["event"]["severity"]
    })
    return result


@app.post("/forecast")
def forecast(payload: ForecastRequest):
    try:
        result = forecast_ml(payload.recent_values, payload.horizon_minutes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    append_csv_log(Path(OUTPUT_DIR) / "service_log.csv", {
        "endpoint": "/forecast",
        "target": payload.target,
        "status": "ok",
        "summary": result["model_output"]["predicted_value"]
    })
    return result


@app.post("/predict-risk")
def predict_risk(payload: RiskRequest):
    result = risk_from_forecast(payload.predicted_value, payload.warning_threshold, payload.high_threshold)
    append_csv_log(Path(OUTPUT_DIR) / "service_log.csv", {
        "endpoint": "/predict-risk",
        "target": payload.target,
        "status": "ok",
        "summary": result["decision"]["risk_level"]
    })
    return result


@app.get("/vision/model-info")
def vision_model_info():
    return _get_vision_model().info()


@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...), top_k: int = Query(default=5, ge=1, le=10)):
    vm = _get_vision_model()
    if not vm.loaded:
        raise HTTPException(status_code=503, detail=vm.info())
    _, image = await _read_image_upload(file)
    try:
        result = vm.classify(image, top_k=top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    top1 = result["model_output"]["predictions"][0]
    append_csv_log(Path(OUTPUT_DIR) / "vision_inference_log.csv", {
        "endpoint": "/classify-image",
        "filename": file.filename or "unknown",
        "content_type": file.content_type or "unknown",
        "status": "ok",
        "top1_class": top1["class_name"],
        "top1_confidence": top1["confidence"],
        "inference_time_ms": result["model_output"]["inference_time_ms"]
    })
    return result


@app.post("/classify-image-annotated")
async def classify_image_annotated(file: UploadFile = File(...), top_k: int = Query(default=5, ge=1, le=10)):
    """Return the uploaded image with the top-1 prediction drawn on it."""
    vm = _get_vision_model()
    if not vm.loaded:
        raise HTTPException(status_code=503, detail=vm.info())
    _, image = await _read_image_upload(file)
    result = vm.classify(image, top_k=top_k)
    annotated = vm.annotate_image(image, result)
    buf = io.BytesIO()
    annotated.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/classify-image-demo", response_class=HTMLResponse)
def classify_image_demo():
    template_path = Path(__file__).parent / "templates" / "classify-image-demo.html"
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
