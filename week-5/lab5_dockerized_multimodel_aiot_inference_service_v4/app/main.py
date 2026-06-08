from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError

from app.schemas import AnomalyRequest, ForecastRequest, RiskRequest
from app.sensor_inference import detect_anomaly_rule, forecast_moving_average, risk_from_forecast
from app.vision_inference import VisionClassifier
from app.logging_utils import append_csv_log

MODEL_DIR = os.getenv("MODEL_DIR", "models")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
VISION_MODEL_PATH = os.getenv("VISION_MODEL_PATH", "models/vision/squeezenet1.1-7.onnx")
VISION_LABELS_PATH = os.getenv("VISION_LABELS_PATH", "models/vision/imagenet_classes.txt")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

app = FastAPI(
    title="Lab 5 - Dockerized Multi-Model AIoT Inference Service",
    version="1.1.0",
    description=(
        "AIoT inference service with sensor endpoints, a lightweight ONNX vision model, "
        "and a simple browser UI for image upload."
    )
)

vision_model = VisionClassifier(VISION_MODEL_PATH, VISION_LABELS_PATH)


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
        "vision_model_loaded": vision_model.loaded
    }


@app.get("/model-info")
def model_info():
    return {
        "service_type": "multi_model_aiot_inference",
        "sensor_models": {
            "anomaly": "zscore_fallback_v1",
            "forecast": "moving_average_baseline_v1"
        },
        "vision_model": vision_model.info(),
        "model_format_learning_path": [
            "Start with framework-native models: PyTorch .pt/.pth and TensorFlow .keras/SavedModel.",
            "Then convert or export to portable inference formats such as ONNX or lightweight edge formats such as TFLite.",
            "Use Docker to package runtime, dependencies, model files, and API behavior into a reproducible service."
        ],
        "note": "Lab 5 focuses on deployment/inference. Stronger sensor models are trained in Lab 3 and Lab 4."
    }


@app.post("/detect-anomaly")
def detect_anomaly(payload: AnomalyRequest):
    result = detect_anomaly_rule(payload.current_value, payload.recent_values, payload.threshold_z)
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
        result = forecast_moving_average(payload.recent_values, payload.horizon_minutes)
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
    return vision_model.info()


@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...), top_k: int = Query(default=5, ge=1, le=10)):
    if not vision_model.loaded:
        raise HTTPException(status_code=503, detail=vision_model.info())
    _, image = await _read_image_upload(file)
    try:
        result = vision_model.classify(image, top_k=top_k)
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
    if not vision_model.loaded:
        raise HTTPException(status_code=503, detail=vision_model.info())
    _, image = await _read_image_upload(file)
    result = vision_model.classify(image, top_k=top_k)
    annotated = vision_model.annotate_image(image, result)
    buf = io.BytesIO()
    annotated.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/classify-image-demo", response_class=HTMLResponse)
def classify_image_demo():
    return """
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Lab 5 - Premium Image Classification Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #060913;
      --bg-card: rgba(15, 23, 42, 0.65);
      --border-light: rgba(255, 255, 255, 0.08);
      --border-glow: rgba(56, 189, 248, 0.25);
      --cyan: #38bdf8;
      --blue: #2563eb;
      --indigo: #6366f1;
      --status-normal: #10b981;
      --status-warning: #f59e0b;
      --status-danger: #ef4444;
      --text-primary: #f3f4f6;
      --text-secondary: #9ca3af;
      --text-muted: #6b7280;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg-base);
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(56, 189, 248, 0.15) 0%, transparent 40%);
      color: var(--text-primary);
      min-height: 100vh;
      padding: 40px 20px;
      line-height: 1.5;
    }

    .container {
      max-width: 1100px;
      margin: 0 auto;
    }

    header {
      text-align: center;
      margin-bottom: 32px;
      animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }

    h1 {
      font-size: 2.25rem;
      font-weight: 700;
      background: linear-gradient(135deg, #ffffff 30%, var(--cyan) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
      letter-spacing: -0.02em;
    }

    .sub {
      color: var(--text-secondary);
      font-size: 1rem;
    }

    .hint-box {
      margin-top: 12px;
      display: inline-block;
      background: rgba(245, 158, 11, 0.08);
      border-left: 4px solid var(--status-warning);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.875rem;
      color: #fbd38d;
      text-align: left;
    }

    /* Double-Bezel Card Layout */
    .card-wrapper {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border-light);
      padding: 6px;
      border-radius: 24px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
      margin-bottom: 24px;
      animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
    }

    .card-inner {
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-radius: 18px;
      padding: 24px;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
    }

    .upload-zone {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }

    .file-input-container {
      position: relative;
      display: inline-block;
      width: 100%;
      max-width: 400px;
    }

    .file-input-trigger {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      padding: 14px 20px;
      background: rgba(255, 255, 255, 0.03);
      border: 2px dashed rgba(255, 255, 255, 0.15);
      border-radius: 14px;
      color: var(--text-secondary);
      font-size: 0.95rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .file-input-trigger:hover {
      background: rgba(255, 255, 255, 0.06);
      border-color: var(--cyan);
      color: var(--text-primary);
    }

    input[type="file"] {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      cursor: pointer;
    }

    .btn-submit {
      background: linear-gradient(135deg, var(--blue), var(--indigo));
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 14px 28px;
      border-radius: 9999px;
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      cursor: pointer;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.25);
    }

    .btn-submit:hover {
      transform: translateY(-2px) scale(1.02);
      box-shadow: 0 10px 25px rgba(99, 102, 241, 0.45);
    }

    .btn-submit:active {
      transform: translateY(1px) scale(0.98);
    }

    .status-badge {
      display: inline-block;
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 0.825rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-light);
      color: var(--text-secondary);
      transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .status-loading {
      background: rgba(245, 158, 11, 0.15);
      border-color: rgba(245, 158, 11, 0.3);
      color: var(--status-warning);
    }

    .status-done {
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.3);
      color: var(--status-normal);
    }

    .status-error {
      background: rgba(239, 68, 68, 0.15);
      border-color: rgba(239, 68, 68, 0.3);
      color: var(--status-danger);
    }

    /* Grid Layout */
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-top: 24px;
    }

    .grid-card-inner {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 300px;
    }

    h3 {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 16px;
      align-self: flex-start;
      border-left: 3px solid var(--cyan);
      padding-left: 8px;
    }

    img {
      max-width: 100%;
      max-height: 380px;
      border-radius: 12px;
      border: 1px solid var(--border-light);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
      display: block;
      transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    img:hover {
      transform: scale(1.015);
    }

    .img-placeholder {
      color: var(--text-muted);
      font-size: 0.9rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }

    /* Table Predictions */
    table {
      border-collapse: collapse;
      width: 100%;
      margin-top: 14px;
      font-size: 0.925rem;
    }

    th, td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border-light);
    }

    th {
      background: rgba(255, 255, 255, 0.02);
      color: var(--text-secondary);
      font-weight: 600;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.01);
    }

    .top1-highlight {
      margin-bottom: 16px;
      padding: 16px;
      background: rgba(56, 189, 248, 0.05);
      border: 1px solid var(--border-glow);
      border-radius: 12px;
      font-size: 1.1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .confidence-pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--cyan);
      font-weight: 600;
      font-size: 0.85rem;
    }

    /* JSON Display */
    pre {
      background: #020408;
      color: #e2e8f0;
      padding: 16px;
      overflow: auto;
      border-radius: 12px;
      font-size: 0.825rem;
      font-family: 'Courier New', Courier, monospace;
      border: 1px solid var(--border-light);
      max-height: 400px;
    }

    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(16px);
        filter: blur(4px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
        filter: blur(0);
      }
    }

    .fadeIn {
      animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @media (max-width: 800px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <span style="display:none">Upload ảnh</span>
  <div class="container">
    <header>
      <h1>AIoT Multi-Model Inference Platform</h1>
      <p class="sub">Hệ thống suy luận dịch vụ tích hợp model ONNX SqueezeNet phân loại 1K lớp</p>
      <div class="hint-box">
        <b>💡 Gợi ý phân tích:</b> Khi kết quả dự đoán (Top-1) có xác suất (Confidence) thấp, hãy phân tích toàn bộ Top-5 và bối cảnh sử dụng trước khi ra quyết định tự động.
      </div>
    </header>

    <!-- Upload Double Bezel Card -->
    <div class="card-wrapper">
      <div class="card-inner upload-zone">
        <div class="file-input-container">
          <div class="file-input-trigger" id="fileLabel">
            <span>📁 Kéo thả hoặc chọn tệp tin ảnh</span>
          </div>
          <input id="file" type="file" accept="image/*" onchange="updateFileName()" />
        </div>
        <button class="btn-submit" onclick="classifyImage()">Chạy Mô Hình Suy Luận</button>
        <span id="status" class="status-badge">Chưa thực hiện inference</span>
      </div>
    </div>

    <!-- Images Preview Grid -->
    <div class="grid">
      <div class="card-wrapper">
        <div class="card-inner grid-card-inner">
          <h3>Ảnh Đầu Vào</h3>
          <img id="preview" style="display:none" />
          <div id="previewHint" class="img-placeholder">
            <span>📷 Chưa có ảnh đầu vào.</span>
          </div>
        </div>
      </div>

      <div class="card-wrapper">
        <div class="card-inner grid-card-inner">
          <h3>Kết Quả Có Nhãn Dự Đoán</h3>
          <img id="annotated" style="display:none" />
          <div id="annotatedHint" class="img-placeholder">
            <span>🎯 Sau khi gọi model, nhãn Top-1 và mức độ tin cậy sẽ được hiển thị trên ảnh.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Predictions Card -->
    <div class="card-wrapper">
      <div class="card-inner">
        <h3>Bảng Dự Đoán Top-5 Classes</h3>
        <div id="top1"></div>
        <table id="predTable" style="display:none">
          <thead>
            <tr>
              <th>Hạng (Rank)</th>
              <th>Lớp Đối Tượng (Class Name)</th>
              <th>Độ Tin Cậy (Confidence)</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <!-- JSON Response Card -->
    <div class="card-wrapper">
      <div class="card-inner">
        <h3>Dữ Liệu JSON Phản Hồi (Inference Output)</h3>
        <pre id="result">Chưa có kết quả phản hồi từ API.</pre>
      </div>
    </div>
  </div>

<script>
function updateFileName() {
  const fileInput = document.getElementById('file');
  const fileLabel = document.getElementById('fileLabel');
  if (fileInput.files.length) {
    fileLabel.innerHTML = `<span>Selected: <b>${fileInput.files[0].name}</b></span>`;
    fileLabel.style.borderColor = 'var(--cyan)';
    fileLabel.style.background = 'rgba(56, 189, 248, 0.03)';
  }
}

async function classifyImage() {
  const fileInput = document.getElementById('file');
  const result = document.getElementById('result');
  const preview = document.getElementById('preview');
  const annotated = document.getElementById('annotated');
  const status = document.getElementById('status');
  const predTable = document.getElementById('predTable');
  const tbody = predTable.querySelector('tbody');
  const top1Div = document.getElementById('top1');
  
  if (!fileInput.files.length) {
    status.textContent = 'Lỗi: Chưa chọn ảnh';
    status.className = 'status-badge status-error';
    result.textContent = 'Hãy chọn một ảnh trước khi bấm chạy mô hình.';
    return;
  }
  
  const file = fileInput.files[0];
  preview.src = URL.createObjectURL(file);
  preview.style.display = 'block';
  document.getElementById('previewHint').style.display = 'none';
  
  status.textContent = 'Đang suy luận...';
  status.className = 'status-badge status-loading';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/classify-image?top_k=5', { method: 'POST', body: formData });
    const data = await res.json();
    
    if (!res.ok) {
      status.textContent = 'Lỗi Hệ Thống';
      status.className = 'status-badge status-error';
      result.textContent = JSON.stringify(data, null, 2);
      return;
    }
    
    result.textContent = JSON.stringify(data, null, 2);
    const preds = data.model_output.predictions;
    const top = preds[0];
    
    top1Div.innerHTML = `
      <div class="top1-highlight fadeIn">
        <span><b>Kết quả dự đoán (Top-1):</b> ${top.class_name}</span>
        <span class="confidence-pill">${(top.confidence * 100).toFixed(1)}%</span>
      </div>`;
      
    tbody.innerHTML = '';
    preds.forEach(p => {
      const row = document.createElement('tr');
      row.className = 'fadeIn';
      row.innerHTML = `
        <td>${p.rank}</td>
        <td><b>${p.class_name}</b></td>
        <td><span class="confidence-pill">${(p.confidence * 100).toFixed(2)}%</span></td>`;
      tbody.appendChild(row);
    });
    
    predTable.style.display = 'table';

    // Fetch annotated image
    const formData2 = new FormData();
    formData2.append('file', file);
    const imgRes = await fetch('/classify-image-annotated?top_k=5', { method: 'POST', body: formData2 });
    
    if (imgRes.ok) {
      const blob = await imgRes.blob();
      annotated.src = URL.createObjectURL(blob);
      annotated.style.display = 'block';
      document.getElementById('annotatedHint').style.display = 'none';
    }
    
    status.textContent = 'Hoàn thành';
    status.className = 'status-badge status-done';
    
  } catch (err) {
    status.textContent = 'Lỗi Kết Nối';
    status.className = 'status-badge status-error';
    result.innerHTML = '<span class="error">Không kết nối được tới API: ' + err + '</span>';
  }
}
</script>
</body>
</html>
"""
