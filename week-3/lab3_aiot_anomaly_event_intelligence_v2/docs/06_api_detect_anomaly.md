# 06 API Detect Anomaly

## API dùng để làm gì?

`src/app.py` deploy model anomaly detection bằng FastAPI. API giúp hệ thống khác gửi telemetry mới và nhận kết quả có cấu trúc:

- Model score.
- Cờ anomaly.
- Event type.
- Severity.
- Decision.
- Explanation.
- Latency.

API này mô phỏng bước đưa model ra khỏi notebook để tích hợp vào hệ thống AIoT.

## Chạy API

Từ thư mục project:

```powershell
uvicorn src.app:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## `GET /health`

### Mục tiêu

Kiểm tra service còn sống và model có load được không.

### Response ví dụ

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_path": "E:\\AIoT\\Day-3\\lab3_aiot_anomaly_event_intelligence_v2\\models\\isolation_forest_iforest_v1.joblib"
}
```

### Cách đọc

- `status = ok`: API process đang chạy.
- `model_loaded = true`: model file tồn tại và đã load.
- `model_loaded = false`: cần chạy train hoặc restart API sau khi model được tạo.

## `GET /model-info`

### Mục tiêu

Trả metadata model và metric offline nếu có `outputs/iforest_metrics.json`.

### Response chính

```json
{
  "model_name": "IsolationForest anomaly detector",
  "model_version": "iforest_v1",
  "input": "history of telemetry points with timestamp and value",
  "output": "anomaly_score, is_anomaly, severity, event_type, decision",
  "metrics": {}
}
```

### Cách dùng

Endpoint này hữu ích cho dashboard hoặc health check nâng cao. Nó giúp biết API đang phục vụ model version nào và metric offline gần nhất là gì.

## `POST /detect-anomaly`

### Mục tiêu

Nhận một cửa sổ telemetry gần nhất và trả kết quả anomaly cho điểm mới nhất.

### Request schema

`AnomalyRequest`:

```json
{
  "history": [
    {
      "timestamp": "2013-07-05 09:00:00",
      "value": 27.5,
      "device_id": "room_temp_01"
    }
  ]
}
```

`history` nên có tối thiểu 36 điểm để rolling feature ổn định, vì `rolling_mean_36` và `zscore_rolling` cần cửa sổ đủ dài.

### Response schema

Response có ba phần:

```json
{
  "model_output": {
    "anomaly_score": 0.6123,
    "is_anomaly": true,
    "model_version": "iforest_v1"
  },
  "event": {
    "event_type": "TEMPERATURE_ANOMALY",
    "device_id": "room_temp_01",
    "timestamp": "2013-07-05 09:00:00",
    "value": 27.5,
    "severity": "MEDIUM",
    "decision": "CREATE_WARNING_EVENT",
    "explanation": "model score indicates unusual pattern",
    "safety_note": "Không tự động điều khiển thiết bị khi anomaly cao; cần xác nhận hoặc rule an toàn."
  },
  "api_check": {
    "latency_ms": 12.34,
    "input_points": 40
  }
}
```

## Flow khi API nhận telemetry mới

Trong `/detect-anomaly`:

1. Kiểm tra model đã load chưa.
2. Chuyển `payload.history` thành DataFrame.
3. Parse `timestamp` bằng pandas.
4. Sort theo timestamp.
5. Tạo feature bằng `add_time_features()`.
6. Lấy dòng mới nhất.
7. Scale feature bằng scaler trong pipeline.
8. Score bằng Isolation Forest.
9. Đảo dấu raw score để score cao hơn nghĩa là bất thường hơn.
10. Chuẩn hóa demo bằng sigmoid.
11. So sánh `score >= 0.55` để tạo `is_anomaly`.
12. Gọi `decision_from_score()` để tạo severity, decision và explanation.
13. Trả JSON response.

## Test bằng Swagger UI

1. Chạy API:

```powershell
uvicorn src.app:app --reload
```

2. Mở:

```text
http://127.0.0.1:8000/docs
```

3. Gọi `GET /health`.

4. Gọi `GET /model-info`.

5. Gọi `POST /detect-anomaly` với body có `history`.

Swagger UI phù hợp để kiểm tra schema và demo thủ công.

## Test bằng `src/test_api.py`

Terminal 1:

```powershell
uvicorn src.app:app --reload
```

Terminal 2:

```powershell
python src/test_api.py
```

Script sẽ:

- Đọc 40 dòng cuối của dataset.
- Gọi `/health`.
- Gọi `/model-info`.
- Gọi `/detect-anomaly`.
- In JSON response.

## Test không cần mở port

Dùng:

```powershell
python src/test_api_local.py
```

Script này dùng `fastapi.testclient.TestClient`, phù hợp khi môi trường lớp học không cho mở port hoặc muốn kiểm tra nhanh response schema.

## Lỗi thường gặp khi API không load được model

### Chưa train model

Triệu chứng:

```json
{
  "model_loaded": false
}
```

Cách xử lý:

```powershell
python src/train_anomaly.py
```

Sau đó restart API.

### Start API sai thư mục

Nếu chạy từ thư mục khác, import path có thể lỗi.

Cách chạy khuyến nghị:

```powershell
cd E:\AIoT\Day-3\lab3_aiot_anomaly_event_intelligence_v2
uvicorn src.app:app --reload
```

### Thiếu dependency

Cài lại:

```powershell
pip install -r requirements.txt
```

### Port 8000 đang bận

Dùng port khác:

```powershell
uvicorn src.app:app --reload --port 8001
```

Khi đó phải sửa URL trong `test_api.py` nếu muốn test bằng script.

### History quá ngắn

API vẫn chạy vì rolling dùng `min_periods`, nhưng score kém tin cậy. Gửi tối thiểu 36 điểm để feature ổn định hơn.

## Nhận xét kỹ thuật

- API đã có schema request rõ ràng bằng Pydantic.
- API trả response tách `model_output`, `event`, `api_check`. Đây là contract tốt cho backend.
- Nếu model chưa load, API trả JSON lỗi nhưng HTTP status vẫn là 200. Production nên dùng `HTTPException(status_code=503)`.
- API không validate history length tối thiểu.
- API normalize score khác training. Đây là điểm quan trọng cần sửa nếu muốn metric offline và behavior online nhất quán.
- `Optional` được import nhưng chưa dùng.

## Đề xuất cải tiến

- Thêm endpoint `/reload-model` hoặc lifecycle startup rõ ràng.
- Lưu threshold trong artifact và dùng lại trong API.
- Trả HTTP status code đúng cho lỗi.
- Thêm request id và model version trong mọi response.
- Ghi event ra database hoặc queue.
- Thêm auth nếu API dùng ngoài môi trường local.
