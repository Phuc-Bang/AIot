# 02. Kiến Trúc Hệ Thống (System Architecture)

Hệ thống được thiết kế theo kiến trúc **API-driven Microservice** khép kín trong môi trường container của Docker. Tất cả các luồng giao tiếp giữa thiết bị IoT hoặc Client bên ngoài với mô hình AI đều được điều phối bởi FastAPI.

---

## 1. Sơ Đồ Kiến Trúc Tổng Thể

Dưới đây là sơ đồ kiến trúc thể hiện cách các thành phần tương tác với nhau từ máy host vật lý đi vào môi trường ảo của Docker container:

```mermaid
graph TB
    subgraph Host Machine (Máy thật)
        Client[Trình duyệt Web / Client HTTP]
        VolumeLogs[(Thư mục outputs/)]
        VolumeModels[(Thư mục models/vision/)]
    end

    subgraph Docker Container (Môi trường ảo)
        direction TB
        PortMapping[Cổng mạng 8000]
        FastAPIServer[FastAPI Application]
        
        subgraph Logic suy luận
            SensorEngine[Sensor Inference Engine]
            VisionEngine[ONNX Vision Classifier]
        end
        
        FileLogs[(/app/outputs/)]
        FileModels[(/app/models/vision/)]
    end

    %% Giao tiếp cổng mạng
    Client -->|Gửi Request cổng 8001| PortMapping
    PortMapping -->|Định tuyến nội bộ| FastAPIServer

    %% Luồng xử lý
    FastAPIServer -->|1. Nhận Telemetry JSON| SensorEngine
    FastAPIServer -->|2. Nhận file ảnh| VisionEngine

    %% Gắn ổ đĩa ảo (Volume mounts)
    FileLogs <==>|Ghi đè thời gian thực| VolumeLogs
    FileModels <==|Đọc file mô hình .onnx| VolumeModels
```

---

## 2. Các Thành Phần Chính Trong Kiến Trúc

### A. Tầng Client (Client Layer)
* **Web UI Dashboard**: Người dùng tương tác trực quan tại `/classify-image-demo` để tải ảnh lên và xem kết quả.
* **IoT Devices / HTTP Clients**: Các cảm biến hoặc thiết bị biên gửi yêu cầu HTTP POST kèm dữ liệu số (JSON payload) hoặc ảnh nhị phân (multipart/form-data) trực tiếp tới các điểm cuối (endpoints) của API.

### B. Tầng Cầu Nối Mạng (Network Bridge)
* **Cổng mạng (Port Mapping)**: Docker ánh xạ cổng vật lý của máy host (`8001`) vào cổng ảo của container (`8000`). Nhờ cơ chế này, dịch vụ có thể chạy cô lập hoàn toàn bên trong container mà vẫn tiếp nhận được yêu cầu từ thế giới bên ngoài.

### C. Tầng Ứng Dụng (Application Layer - FastAPI)
* Đóng vai trò là người tiếp đón và điều phối. FastAPI nhận dữ liệu đầu vào, thực hiện kiểm tra định dạng dữ liệu (validation nhờ thư viện Pydantic), phân phối dữ liệu cho các bộ máy suy luận (inference engines) tương ứng, ghi log và đóng gói dữ liệu đầu ra trả về cho Client dưới dạng chuẩn JSON hoặc dữ liệu luồng ảnh (StreamingResponse).

### D. Tầng Suy Luận AI (Inference Layer)
* **Bộ máy phân tích cảm biến (Sensor Inference Engine)**: Thực hiện tính toán z-score để phát hiện dị thường và phương pháp trung bình trượt (Moving Average) để dự báo chỉ số tiếp theo.
* **Bộ máy phân loại ảnh (ONNX Vision Classifier)**: Khởi tạo phiên làm việc với mô hình `onnxruntime` trên nền phần cứng CPU (`CPUExecutionProvider`). Thực hiện các thuật toán tiền xử lý ma trận ảnh gốc sang Tensor chuẩn hóa và áp dụng hàm Softmax để xác định nhãn vật thể.

### E. Tầng Lưu Trữ Lưu Đệm (Storage & Volume Layer)
* **Volume Mounts**: Liên kết các thư mục lưu trữ tĩnh giữa máy host và Docker container.
  * Thư mục `models/` giúp đưa file mô hình dung lượng lớn vào container một cách an toàn mà không làm phình kích thước Docker Image.
  * Thư mục `outputs/` làm nhiệm vụ ghi lại toàn bộ nhật ký sự kiện, đảm bảo dữ liệu ghi log được lưu vĩnh viễn trên máy thật của bạn.
