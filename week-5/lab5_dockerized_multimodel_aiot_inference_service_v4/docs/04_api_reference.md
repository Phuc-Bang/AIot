# 04. Tài Liệu API Tham Chiếu (API Reference)

Tài liệu này đặc tả chi tiết tất cả các Web API Endpoints được cung cấp bởi dịch vụ suy luận AIoT đa mô hình. Hệ thống sử dụng chuẩn giao thức HTTP RESTful, trao đổi dữ liệu qua định dạng JSON hoặc Multipart Form Data (đối với ảnh).

---

## 1. Bảng Tổng Hợp Danh Sách Endpoints

| Phương Thức | Đường Dẫn (Route) | Phân Loại | Chức Năng |
|:---:|---|---|---|
| **GET** | `/health` | Hệ thống | Kiểm tra trạng thái hoạt động và sức khỏe của dịch vụ. |
| **GET** | `/model-info` | Hệ thống | Xem thông tin các phiên bản mô hình AI đang chạy. |
| **POST** | `/detect-anomaly` | Cảm biến (Sensor) | Phân tích dị thường dữ liệu cảm biến thời gian thực. |
| **POST** | `/forecast` | Cảm biến (Sensor) | Dự báo chỉ số cảm biến ở chu kỳ thời gian tiếp theo. |
| **POST** | `/predict-risk` | Cảm biến (Sensor) | Đánh giá mức độ rủi ro dựa trên chỉ số dự báo. |
| **GET** | `/vision/model-info` | Hình ảnh (Vision) | Xem thông tin chi tiết về mô hình ảnh ONNX đang nạp. |
| **POST** | `/classify-image` | Hình ảnh (Vision) | Tải ảnh lên để phân loại, trả về kết quả JSON Top-K. |
| **POST** | `/classify-image-annotated` | Hình ảnh (Vision) | Tải ảnh lên để phân loại, trả về luồng ảnh vẽ sẵn nhãn. |
| **GET** | `/classify-image-demo` | Giao diện (Web) | Giao diện HTML kiểm thử upload phân loại ảnh trực quan. |

---

## 2. Chi Tiết Các Endpoints Hệ Thống

### A. Endpoint `/health` [GET]
* **Mô tả**: Dùng bởi các hệ thống giám sát (như Kubernetes hoặc Docker Healthcheck) để kiểm tra xem API và mô hình đã sẵn sàng hoạt động hay chưa.
* **Response Mẫu (200 OK)**:
  ```json
  {
    "service_status": "ok",
    "model_dir": "models",
    "output_dir": "outputs",
    "vision_model_loaded": true
  }
  ```

---

## 3. Chi Tiết Các Endpoints Cảm Biến (Sensor)

### A. Endpoint `/detect-anomaly` [POST]
* **Mô tả**: Nhận giá trị cảm biến hiện tại và danh sách lịch sử gần nhất để tính toán chỉ số Z-Score, từ đó xác định xem điểm dữ liệu hiện tại có bất thường hay không.
* **Request Payload (JSON)**:
  ```json
  {
    "target": "temperature",
    "current_value": 34.0,
    "recent_values": [27.1, 27.3, 27.2, 27.4, 27.5],
    "threshold_z": 2.5
  }
  ```
* **Response Mẫu (200 OK)**:
  ```json
  {
    "model_output": {
      "anomaly_score": 9.380832,
      "threshold_used": 2.5,
      "is_anomaly": true,
      "model_version": "zscore_fallback_v1"
    },
    "event": {
      "severity": "HIGH",
      "decision": "CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK",
      "explanation": "z-score=9.381, mean=27.300, std=0.141",
      "safety_note": "Không tự động điều khiển thiết bị chỉ dựa trên một điểm anomaly."
    }
  }
  ```

### B. Endpoint `/forecast` [POST]
* **Mô tả**: Nhận danh sách các giá trị lịch sử để chạy thuật toán dự báo giá trị tiếp theo.
* **Request Payload (JSON)**:
  ```json
  {
    "target": "co2",
    "recent_values": [800.0, 840.0, 870.0, 910.0, 950.0],
    "horizon_minutes": 15
  }
  ```
* **Response Mẫu (200 OK)**:
  ```json
  {
    "model_output": {
      "predicted_value": 874.0,
      "last_value": 950.0,
      "forecast_delta": -76.0,
      "forecast_horizon_minutes": 15,
      "model_version": "moving_average_baseline_v1"
    },
    "evaluation_hint": {
      "note": "Lab 5 dùng baseline inference demo. Metric đầy đủ đã học ở Lab 4."
    }
  }
  ```

---

## 4. Chi Tiết Các Endpoints Hình Ảnh (Vision)

### A. Endpoint `/classify-image` [POST]
* **Mô tả**: Nhận dữ liệu tệp tin hình ảnh nhị phân từ camera, chạy tiền xử lý và suy luận qua mô hình SqueezeNet để trả về danh sách Top-K nhãn lớp dự đoán có xác suất cao nhất.
* **Request Headers**: `Content-Type: multipart/form-data`
* **Request Parameters**:
  * `file`: File ảnh dạng binary (JPEG/PNG).
  * `top_k` (Query parameter): Số lượng kết quả muốn lấy (Từ 1 đến 10, mặc định là 5).
* **Response Mẫu (200 OK)**:
  ```json
  {
    "model_output": {
      "task": "image_classification",
      "model_name": "squeezenet1.1_onnx_imagenet1k",
      "model_version": "vision_squeezenet_onnx_v2",
      "model_format": "ONNX",
      "top_k": 5,
      "predictions": [
        {
          "rank": 1,
          "class_id": 681,
          "class_name": "notebook, notebook computer",
          "confidence": 0.892415
        },
        {
          "rank": 2,
          "class_id": 620,
          "class_name": "laptop, laptop computer",
          "confidence": 0.081245
        }
      ],
      "inference_time_ms": 14.524
    },
    "decision": {
      "confidence_level": "HIGH",
      "recommendation": "USE_WITH_CONTEXT",
      "safety_note": "This is a general ImageNet-1K classifier, not a domain-specific safety, medical, or plant-disease model."
    }
  }
  ```

### B. Endpoint `/classify-image-annotated` [POST]
* **Mô tả**: Giống `/classify-image` nhưng thay vì trả dữ liệu JSON, API vẽ một khung tiêu đề chứa nhãn dự đoán Top-1 và mức độ tự tin trực tiếp lên góc trái trên của ảnh gốc, sau đó trả về luồng dữ liệu ảnh mới để hiển thị ngay trên web.
* **Response**: Tệp tin ảnh nhị phân dạng `image/png`.
